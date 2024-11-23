import json
import requests
import sys
import os
import base64
import signal
import time
from tqdm import tqdm
from datetime import datetime

from config import Config
from embedding_generator import EmbeddingGenerator
from opensearch_client import OpenSearchClient

class BatchImporter:
    def __init__(self):
        self.keep_running = True
        signal.signal(signal.SIGINT, self.handle_interrupt)
        signal.signal(signal.SIGTERM, self.handle_interrupt)
        
        try:
            Config.validate_config()
            aws_session = Config.get_aws_session()
            
            try:
                bedrock_client = aws_session.client('bedrock-runtime')
                test_text = "test"
                test_body = json.dumps({"inputText": test_text})
                bedrock_client.invoke_model(
                    body=test_body,
                    modelId=Config.EMVEDDINGMODEL_ID,
                    accept="application/json",
                    contentType="application/json"
                )
            except Exception as e:
                print(f"Error testing Bedrock connection: {str(e)}")
                sys.exit(1)
            
            self.embedding_generator = EmbeddingGenerator(bedrock_client)
            self.opensearch_client = OpenSearchClient(aws_session)
            self.opensearch_client.ensure_index_exists()
            
            # File paths for tracking progress and errors
            self.progress_file = "import_progress.txt"
            self.error_log_file = f"import_errors_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            self.retry_delay = 5  # seconds between retries
            self.max_retries = 3  # maximum number of retries for failures
        except Exception as e:
            print(f"Error initializing BatchImporter: {str(e)}")
            sys.exit(1)
    
    def handle_interrupt(self, signum, frame):
        """Handle interrupt signals gracefully"""
        print("\nReceived interrupt signal. Completing current record before shutting down...")
        self.keep_running = False
        
    def download_image(self, url, max_retries=3):
        """Download image with retry mechanism"""
        for attempt in range(max_retries):
            try:
                response = requests.get(url, timeout=30)
                if response.status_code == 200:
                    image_data = base64.b64encode(response.content).decode('utf-8')
                    return image_data
                if response.status_code == 404:  # Don't retry if image not found
                    return None
            except requests.RequestException:
                if attempt < max_retries - 1:
                    time.sleep(self.retry_delay)
                continue
        return None

    def get_last_processed_line(self):
        """Get the last successfully processed line number"""
        try:
            if os.path.exists(self.progress_file):
                with open(self.progress_file, 'r') as f:
                    content = f.read().strip()
                    print(f"Debug: Progress file content = '{content}'")  # Debug print
                    if content:  # Only try to convert if content is not empty
                        return int(content)
            return 0
        except Exception as e:
            print(f"Warning: Error reading progress file: {str(e)}")
            return 0

    def save_progress(self, line_number):
        """Save the current progress"""
        try:
            with open(self.progress_file, 'w') as f:
                f.write(str(line_number))
        except Exception as e:
            print(f"Warning: Error saving progress: {str(e)}")
            
    def log_error(self, line_number, error_msg):
        """Log errors with timestamp"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(self.error_log_file, 'a') as f:
            f.write(f"[{timestamp}] Line {line_number}: {error_msg}\n")

    def process_record(self, record, line_number):
        """Process a single record with retry mechanism"""
        for attempt in range(self.max_retries):
            try:
                description_text = " ".join(filter(None, [
                    record.get('title', ''),
                    " ".join(record.get('features', [])),
                    " ".join(record.get('description', [])),
                    record.get('main_category', ''),
                    " ".join(record.get('categories', []))
                ]))
                
                if not description_text.strip():
                    self.log_error(line_number, "Empty description text")
                    return False
                
                try:
                    description_embedding = self.embedding_generator.generate_embedding(description_text, 'text')
                    if not description_embedding or not isinstance(description_embedding, list):
                        raise Exception("Invalid description embedding format")
                except Exception as e:
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay)
                        continue
                    self.log_error(line_number, f"Error generating description embedding: {str(e)}")
                    return False

                image_embedding = None
                image_url = None
                if record.get('images') and len(record['images']) > 0:
                    first_image = record['images'][0]
                    if 'hi_res' in first_image:
                        image_url = first_image['hi_res']
                        image_data = self.download_image(image_url)
                        if image_data:
                            try:
                                image_embedding = self.embedding_generator.generate_embedding(image_data, 'image')
                                if not image_embedding or not isinstance(image_embedding, list):
                                    raise Exception("Invalid image embedding format")
                            except Exception as e:
                                # Don't retry for image embedding failures
                                self.log_error(line_number, f"Error generating image embedding: {str(e)}")
                                image_embedding = None

                document = {
                    'id': record.get('parent_asin', ''),
                    'title': record.get('title', ''),
                    'main_category': record.get('main_category', ''),
                    'categories': record.get('categories', []),
                    'features': record.get('features', []),
                    'description': description_text,
                    'price': record.get('price', 0),
                    'average_rating': record.get('average_rating', 0),
                    'rating_number': record.get('rating_number', 0),
                    'store': record.get('store', ''),
                    'description_embedding': description_embedding
                }
                
                if image_url and image_embedding:
                    document['image_url'] = image_url
                    document['image_embedding'] = image_embedding

                self.opensearch_client.index_document(document)
                return True
                
            except Exception as e:
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                self.log_error(line_number, f"Error processing record: {str(e)}")
                return False
        
        return False

    def process_file(self, file_path, limit=0):
        """Process the input file with progress tracking and error handling"""
        last_processed = self.get_last_processed_line()
        current_line = 0
        success_count = 0
        error_count = 0
        start_time = time.time()
        last_save_time = start_time

        print(f"Resuming from line {last_processed}")
        if limit > 0:
            print(f"Processing {limit} records")
        
        try:
            with open(file_path, 'r') as f:
                total_lines = sum(1 for _ in f)
                if limit > 0:
                    total_lines = min(total_lines, limit)
                f.seek(0)
                
                with tqdm(total=total_lines, initial=last_processed) as pbar:
                    for line in f:
                        if not self.keep_running:
                            print("\nGracefully shutting down...")
                            break
                            
                        current_line += 1
                        
                        if current_line <= last_processed:
                            continue
                        
                        try:
                            record = json.loads(line.strip())
                            if self.process_record(record, current_line):
                                success_count += 1
                            else:
                                error_count += 1
                        except json.JSONDecodeError as e:
                            self.log_error(current_line, f"Error parsing JSON: {str(e)}")
                            error_count += 1
                        except Exception as e:
                            self.log_error(current_line, f"Unexpected error: {str(e)}")
                            error_count += 1
                        
                        # Save progress every 5 minutes
                        current_time = time.time()
                        if current_time - last_save_time >= 300:
                            self.save_progress(current_line)
                            last_save_time = current_time
                            
                        pbar.update(1)

                        if limit > 0 and (success_count + error_count) >= limit:
                            break
                        
                    # Save final progress
                    self.save_progress(current_line)
                    
            duration = time.time() - start_time
            print(f"\nProcessing completed in {duration:.2f} seconds:")
            print(f"Total processed: {current_line}")
            print(f"Successful: {success_count}")
            print(f"Failed: {error_count}")
            print(f"Error log: {self.error_log_file}")
        except Exception as e:
            print(f"Fatal error processing file: {str(e)}")
            sys.exit(1)

def main():
    # Print all arguments for debugging
    print("Debug: sys.argv =", sys.argv)
    
    if len(sys.argv) < 2:
        print("Usage: python batch_import_to_opensearch.py <json_file_path> [limit]")
        print("  limit: 0 for importing all records (default), or a positive number for limited import")
        sys.exit(1)

    file_path = sys.argv[1]
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        sys.exit(1)

    # Initialize limit with default value
    limit = 0

    # Only try to parse limit if we have more than 2 arguments
    if len(sys.argv) > 2:
        try:
            # Get the raw limit argument
            limit_str = sys.argv[2]
            print(f"Debug: Raw limit argument = '{limit_str}'")
            
            # If the argument is not empty and contains digits
            if limit_str and limit_str.strip().isdigit():
                limit = int(limit_str)
                if limit < 0:
                    print("Error: Limit must be 0 or a positive number")
                    sys.exit(1)
            else:
                print(f"Error: Invalid limit argument '{limit_str}'. Must be a positive number.")
                sys.exit(1)
                
        except ValueError as e:
            print(f"Error parsing limit: {str(e)}")
            sys.exit(1)

    try:
        importer = BatchImporter()
        importer.process_file(file_path, limit)
    except KeyboardInterrupt:
        print("\nProcess interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()

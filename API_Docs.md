# Image Processing API Documentation

## Overview

This API provides endpoints for uploading, updating, searching, and deleting images with their associated metadata and vector embeddings.

## Base URL

`https://your-api-endpoint`

## Endpoints

### 1. Upload Image

Upload a new image with metadata.

**Endpoint:** `POST /images`

**Request Schema:**

```json
{
    "image": "string",       // Base64 encoded image data
    "description": "string", // Optional
    "tags": ["string"]      // Optional array of tags
}
```

**Response Schema:**

```json
{
    "status": "success",
    "message": "Image uploaded successfully",
    "data": {
        "image_id": "string" // UUID of the uploaded image
    }
}
```

**Curl Example:**

```bash
curl -X POST https://your-api-endpoint/images \
  -H "Content-Type: application/json" \
  -d '{
    "image": "base64_encoded_image_data",
    "description": "A beautiful sunset",
    "tags": ["sunset", "nature", "landscape"]
  }'
```

### 2. Update Image Metadata

Update metadata for an existing image.

**Endpoint:** `PUT /images`

**Request Schema:**

```json
{
    "image_id": "string",
    "description": "string",  // Optional
    "tags": ["string"]       // Optional array of tags
}
```

**Response Schema:**

```json
{
    "status": "success",
    "message": "Image metadata updated successfully",
    "data": {
        "image_id": "string"
    }
}
```

**Curl Example:**

```bash
curl -X PUT https://your-api-endpoint/images \
  -H "Content-Type: application/json" \
  -d '{
    "image_id": "123e4567-e89b-12d3-a456-426614174000",
    "description": "Updated description",
    "tags": ["updated", "tags"]
  }'
```

### 3. Search Images

Search for similar images using either an image or text query.

**Endpoint:** `POST /images/search`

**Request Schema:**

```json
{
    "query_image": "string",  // Optional: Base64 encoded image
    "query_text": "string",   // Optional: Text query
    "rerank": "string",      // Optional: "True" | "False", "False" by default
    "k": 10                  // Optional: Number of results (default: 10)
}
```

**Response Schema:**

```json
{
    "status": "success",
    "message": "Search completed successfully",
    "data": {
        "results": [
            {
                "id": "string",
                "description": "string",
                "tags": ["string"],
                "score": "number"
            }
        ]
    }
}
```

**Curl Example (Image Search):**

```bash
curl -X POST https://your-api-endpoint/images/search \
  -H "Content-Type: application/json" \
  -d '{
    "query_image": "base64_encoded_image_data",
    "k": 5
  }'
```

**Curl Example (Text Search):**

```bash
curl -X POST https://your-api-endpoint/images/search \
  -H "Content-Type: application/json" \
  -d '{
    "query_text": "sunset on beach",
    "k": 5
  }'
```

### 4. Delete Image

Delete an image and its associated metadata.

**Endpoint:** `DELETE /images/{image_id}`

**Response Schema:**

```json
{
    "status": "success",
    "message": "Image deleted successfully",
    "data": {
        "image_id": "string"
    }
}
```

**Curl Example:**

```bash
curl -X DELETE https://your-api-endpoint/images/123e4567-e89b-12d3-a456-426614174000
```

## Error Responses

All endpoints may return error responses in the following format:

```json
{
    "status": "error",
    "code": number,
    "message": "string",
    "data": {
        "error_code": "string",
        "details": {}
    }
}
```

Common error codes:

* 400: Bad Request (Invalid input)
* 404: Not Found (Image not found)
* 500: Internal Server Error

## Notes

* Image data must be Base64 encoded
* At least one of `query_image` or `query_text` must be provided for search requests
* The API uses vector embeddings for similarity search
* All requests must include `Content-Type: application/json` header

#!/bin/bash
# Get caller identity ARN
CALLER_ARN=$(aws sts get-caller-identity --query 'Arn' --output text)
echo "Caller ARN: $CALLER_ARN"

# Export as CDK context
echo "{\"callerArn\": \"$CALLER_ARN\"}" > cdk.context.json

# import boto3
# import json
# import os
# from dotenv import load_dotenv
#
# load_dotenv()
#
# s3_client = boto3.client("s3")
# BUCKET_NAME = os.getenv("BUCKET_NAME")
#
#
# def save_chat_history_to_s3(username, history):
#     """Save the user's chat history as a JSON file in S3."""
#     key = f"{username}/chat_history.json"
#     data = json.dumps(history)
#     s3_client.put_object(Bucket=BUCKET_NAME, Key=key, Body=data)
#
#
# def load_chat_history_from_s3(username):
#     """Load the user's chat history from S3."""
#     key = f"{username}/chat_history.json"
#     try:
#         response = s3_client.get_object(Bucket=BUCKET_NAME, Key=key)
#         data = response['Body'].read().decode('utf-8')
#         return json.loads(data)
#     except s3_client.exceptions.NoSuchKey:
#         # No chat history yet
#         return []

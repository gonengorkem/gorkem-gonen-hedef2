import os
import boto3
from botocore.exceptions import ClientError
from typing import Optional

# Fetch environment configuration
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL") # Useful for MinIO / LocalStack

class StorageService:
    def __init__(self):
        self.is_s3_enabled = False
        self.s3_client = None
        
        # Check if S3 credentials and bucket name are provided
        if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY and S3_BUCKET_NAME:
            try:
                # Initialize S3 client
                session = boto3.Session(
                    aws_access_key_id=AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                    region_name=AWS_REGION
                )
                
                client_kwargs = {}
                if S3_ENDPOINT_URL:
                    client_kwargs["endpoint_url"] = S3_ENDPOINT_URL
                    
                self.s3_client = session.client("s3", **client_kwargs)
                self.is_s3_enabled = True
                print(f"[StorageService] AWS S3 standard storage initialized. Bucket: {S3_BUCKET_NAME}")
            except Exception as e:
                print(f"[StorageService] Failed to initialize S3 client: {str(e)}. Falling back to local storage.")
        else:
            print("[StorageService] S3 variables not complete. Using local storage mode.")

    def save_file(self, file_content: bytes, destination_path: str) -> str:
        """
        Saves a file. If S3 is enabled, uploads to S3. Otherwise, writes to local disk.
        Returns the public URL, S3 URI, or local path.
        """
        if self.is_s3_enabled and self.s3_client:
            try:
                # S3 keys should not start with a slash
                s3_key = destination_path.replace("\\", "/").lstrip("/")
                self.s3_client.put_object(
                    Bucket=S3_BUCKET_NAME,
                    Key=s3_key,
                    Body=file_content
                )
                print(f"[StorageService] File successfully uploaded to S3: s3://{S3_BUCKET_NAME}/{s3_key}")
                # Return the s3-compatible URL or key
                return f"s3://{S3_BUCKET_NAME}/{s3_key}"
            except ClientError as e:
                print(f"[StorageService] S3 upload error: {e}. Falling back to write locally.")
        
        # Local fallback
        # Ensure parent directories exist
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)
        with open(destination_path, "wb") as f:
            f.write(file_content)
        print(f"[StorageService] File saved locally at: {destination_path}")
        return destination_path

    def load_file(self, source_path: str) -> Optional[bytes]:
        """
        Loads a file. If S3 is enabled and the source path is an S3 URL/key, retrieves from S3.
        Otherwise, reads from local disk.
        """
        # If source_path starts with s3://
        if source_path.startswith("s3://") or (self.is_s3_enabled and not os.path.isabs(source_path)):
            if self.is_s3_enabled and self.s3_client:
                try:
                    s3_key = source_path
                    if source_path.startswith("s3://"):
                        # Extract key from s3://bucket/key
                        parts = source_path[5:].split("/", 1)
                        if len(parts) == 2:
                            s3_key = parts[1]
                    
                    s3_key = s3_key.replace("\\", "/").lstrip("/")
                    response = self.s3_client.get_object(Bucket=S3_BUCKET_NAME, Key=s3_key)
                    return response["Body"].read()
                except ClientError as e:
                    print(f"[StorageService] S3 load error: {e}")
                    return None
            else:
                # If path starts with s3:// but S3 is not enabled, we cannot read it unless it's cached locally
                print(f"[StorageService] Cannot load '{source_path}' because S3 is not enabled.")
                return None
                
        # Local load
        if os.path.exists(source_path):
            try:
                with open(source_path, "rb") as f:
                    return f.read()
            except Exception as e:
                print(f"[StorageService] Local load error: {e}")
                return None
        return None

    def delete_file(self, source_path: str) -> bool:
        """
        Deletes a file from S3 or local storage.
        """
        if source_path.startswith("s3://") or (self.is_s3_enabled and not os.path.isabs(source_path)):
            if self.is_s3_enabled and self.s3_client:
                try:
                    s3_key = source_path
                    if source_path.startswith("s3://"):
                        parts = source_path[5:].split("/", 1)
                        if len(parts) == 2:
                            s3_key = parts[1]
                    s3_key = s3_key.replace("\\", "/").lstrip("/")
                    self.s3_client.delete_object(Bucket=S3_BUCKET_NAME, Key=s3_key)
                    return True
                except ClientError as e:
                    print(f"[StorageService] S3 delete error: {e}")
                    return False
            else:
                return False
                
        if os.path.exists(source_path):
            try:
                os.remove(source_path)
                return True
            except Exception as e:
                print(f"[StorageService] Local delete error: {e}")
                return False
        return False

    def list_files(self, prefix: str) -> list:
        """
        Lists filenames under the given prefix. If S3 is enabled, lists S3 objects.
        Otherwise, lists local files under that directory.
        """
        if self.is_s3_enabled and self.s3_client:
            try:
                s3_prefix = prefix.replace("\\", "/").lstrip("/")
                response = self.s3_client.list_objects_v2(
                    Bucket=S3_BUCKET_NAME,
                    Prefix=s3_prefix
                )
                files = []
                if "Contents" in response:
                    for obj in response["Contents"]:
                        key = obj["Key"]
                        filename = os.path.basename(key)
                        if filename:
                            files.append(filename)
                return files
            except ClientError as e:
                print(f"[StorageService] S3 list error: {e}")
                return []
        
        # Local list
        local_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), prefix)
        if os.path.exists(local_dir):
            return [f for f in os.listdir(local_dir) if os.path.isfile(os.path.join(local_dir, f))]
        return []

# Export a singleton instance
storage_service = StorageService()


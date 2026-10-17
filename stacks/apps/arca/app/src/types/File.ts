export interface FileMetadata {
  id: string;
  originalName: string;
  savedName: string;
  size: number;
  uploadDate: Date;
  mimetype: string;
}

export interface UploadResponse {
  success: boolean;
  message: string;
  file?: FileMetadata;
}

export interface ListFilesResponse {
  success: boolean;
  files: FileMetadata[];
  totalSize: number;
}

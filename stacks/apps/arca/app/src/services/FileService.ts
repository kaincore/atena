import fs from 'fs/promises';
import path from 'path';
import { FileMetadata } from '../types/File';

export class FileService {
  private uploadsDir: string;
  private metadataFile: string;

  constructor(uploadsDir: string = './uploads') {
    this.uploadsDir = uploadsDir;
    this.metadataFile = './data/metadata.json';
    this.ensureUploadsDirExists();
  }

  private async ensureUploadsDirExists(): Promise<void> {
    try {
      await fs.access(this.uploadsDir);
    } catch {
      await fs.mkdir(this.uploadsDir, { recursive: true });
    }
  }

  private async loadMetadata(): Promise<FileMetadata[]> {
    try {
      const data = await fs.readFile(this.metadataFile, 'utf-8');
      return JSON.parse(data);
    } catch {
      return [];
    }
  }

  private async saveMetadata(metadata: FileMetadata[]): Promise<void> {
    await fs.writeFile(this.metadataFile, JSON.stringify(metadata, null, 2));
  }

  async addFile(fileData: {
    originalName: string;
    savedName: string;
    size: number;
    mimetype: string;
  }): Promise<FileMetadata> {
    const metadata = await this.loadMetadata();
    
    const fileMetadata: FileMetadata = {
      id: Date.now().toString(),
      ...fileData,
      uploadDate: new Date()
    };

    metadata.push(fileMetadata);
    await this.saveMetadata(metadata);
    
    return fileMetadata;
  }

  async listFiles(): Promise<{ files: FileMetadata[]; totalSize: number }> {
    const files = await this.loadMetadata();
    const totalSize = files.reduce((sum, file) => sum + file.size, 0);
    
    return { files, totalSize };
  }

  async getFile(id: string): Promise<FileMetadata | null> {
    const files = await this.loadMetadata();
    return files.find(file => file.id === id) || null;
  }

  async deleteFile(id: string): Promise<boolean> {
    const files = await this.loadMetadata();
    const fileIndex = files.findIndex(file => file.id === id);
    
    if (fileIndex === -1) return false;

    const file = files[fileIndex];
    const filePath = path.join(this.uploadsDir, file.savedName);
    
    try {
      await fs.unlink(filePath);
      files.splice(fileIndex, 1);
      await this.saveMetadata(files);
      return true;
    } catch {
      return false;
    }
  }

  getFilePath(savedName: string): string {
    return path.join(this.uploadsDir, savedName);
  }
}

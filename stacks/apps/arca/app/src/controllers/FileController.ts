import { Request, Response } from 'express';
import { FileService } from '../services/FileService';
import path from 'path';

const fileService = new FileService();

export class FileController {
  async upload(req: Request, res: Response): Promise<void> {
    try {
      if (!req.files || !req.files.file) {
        res.status(400).json({
          success: false,
          message: 'Nenhum arquivo foi enviado'
        });
        return;
      }

      const file = Array.isArray(req.files.file) ? req.files.file[0] : req.files.file;
      // nome vindo do navegador: sem pastas nem caracteres de controle, para não escapar de uploads/
      file.name = path.basename(file.name.replace(/\\/g, '/')).replace(/[\x00-\x1f\x7f]/g, '').slice(0, 200) || 'arquivo';
      const savedName = `${Date.now()}-${file.name}`;
      const uploadPath = fileService.getFilePath(savedName);

      await file.mv(uploadPath);

      const fileMetadata = await fileService.addFile({
        originalName: file.name,
        savedName,
        size: file.size,
        mimetype: file.mimetype
      });

      res.json({
        success: true,
        message: 'Arquivo enviado com sucesso',
        file: fileMetadata
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        message: 'Erro ao fazer upload do arquivo'
      });
    }
  }

  async list(req: Request, res: Response): Promise<void> {
    try {
      const { files, totalSize } = await fileService.listFiles();
      
      res.json({
        success: true,
        files,
        totalSize
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        message: 'Erro ao listar arquivos'
      });
    }
  }

  async download(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const file = await fileService.getFile(id);

      if (!file) {
        res.status(404).json({
          success: false,
          message: 'Arquivo não encontrado'
        });
        return;
      }

      const filePath = fileService.getFilePath(file.savedName);
      res.download(filePath, file.originalName);
    } catch (error) {
      res.status(500).json({
        success: false,
        message: 'Erro ao baixar arquivo'
      });
    }
  }

  async delete(req: Request, res: Response): Promise<void> {
    try {
      const { id } = req.params;
      const success = await fileService.deleteFile(id);

      if (!success) {
        res.status(404).json({
          success: false,
          message: 'Arquivo não encontrado'
        });
        return;
      }

      res.json({
        success: true,
        message: 'Arquivo excluído com sucesso'
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        message: 'Erro ao excluir arquivo'
      });
    }
  }
}

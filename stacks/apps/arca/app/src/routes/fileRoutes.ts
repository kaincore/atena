import { Router } from 'express';
import { FileController } from '../controllers/FileController';

const router = Router();
const fileController = new FileController();

router.post('/upload', (req, res) => fileController.upload(req, res));
router.get('/files', (req, res) => fileController.list(req, res));
router.get('/files/:id', (req, res) => fileController.download(req, res));
router.delete('/files/:id', (req, res) => fileController.delete(req, res));

export default router;

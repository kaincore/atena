import express from 'express';
import fileUpload from 'express-fileupload';
import path from 'path';
import fileRoutes from './routes/fileRoutes';

const app = express();
const PORT = process.env.PORT || 3002;

app.use(express.json());
app.use(express.static(path.join(__dirname, '../public')));
app.use(fileUpload({
  createParentPath: true,
  defParamCharset: 'utf8', // navegadores mandam o nome em UTF-8; sem isso, acentos chegam corrompidos
  limits: {
    fileSize: 50 * 1024 * 1024 // 50MB max
  },
  abortOnLimit: true, // acima do limite, recusa em vez de salvar o arquivo cortado
  responseOnLimit: JSON.stringify({ success: false, message: 'Arquivo maior que 50 MB' }),
}));

app.use('/api', fileRoutes);

app.listen(PORT, () => {
  console.log(`[ARCA] Sistema iniciado na porta ${PORT}`);
});

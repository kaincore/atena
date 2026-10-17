const uploadForm = document.getElementById('uploadForm');
const fileInput = document.getElementById('fileInput');
const uploadStatus = document.getElementById('uploadStatus');
const filesList = document.getElementById('filesList');
const filesInfo = document.getElementById('filesInfo');

function formatBytes(bytes) {
  if (bytes === 0) return '0 Bytes';
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

function escapeHtml(text) {
  return String(text).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function formatDate(dateString) {
  const date = new Date(dateString);
  return date.toLocaleString('pt-BR');
}

async function loadFiles() {
  try {
    const response = await fetch('/api/files');
    const data = await response.json();

    if (data.success) {
      filesInfo.textContent = `Total: ${data.files.length} arquivo(s) | Tamanho Total: ${formatBytes(data.totalSize)}`;
      
      if (data.files.length === 0) {
        filesList.innerHTML = '<div class="empty-message">Nenhum arquivo armazenado</div>';
        return;
      }

      filesList.innerHTML = data.files.map(file => `
        <div class="file-item">
          <div class="file-info">
            <div class="file-name">${escapeHtml(file.originalName)}</div>
            <div class="file-meta">
              Tamanho: ${formatBytes(file.size)} |
              Data: ${formatDate(file.uploadDate)} |
              Tipo: ${escapeHtml(file.mimetype)}
            </div>
          </div>
          <div class="file-actions">
            <button class="btn-small" data-action="download" data-id="${escapeHtml(file.id)}">
              Download
            </button>
            <button class="btn-small delete" data-action="delete" data-id="${escapeHtml(file.id)}">
              Excluir
            </button>
          </div>
        </div>
      `).join('');
    }
  } catch (error) {
    showStatus('Erro ao carregar arquivos', 'error');
  }
}

function showStatus(message, type) {
  uploadStatus.textContent = message;
  uploadStatus.className = `status ${type}`;
  setTimeout(() => {
    uploadStatus.textContent = '';
    uploadStatus.className = 'status';
  }, 3000);
}

uploadForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  
  const file = fileInput.files[0];
  if (!file) {
    showStatus('Selecione um arquivo', 'error');
    return;
  }

  const formData = new FormData();
  formData.append('file', file);

  try {
    showStatus('Enviando arquivo...', 'success');
    
    const response = await fetch('/api/upload', {
      method: 'POST',
      body: formData
    });

    const data = await response.json();

    if (data.success) {
      showStatus('Arquivo enviado com sucesso', 'success');
      fileInput.value = '';
      await loadFiles();
    } else {
      showStatus(data.message || 'Erro ao enviar arquivo', 'error');
    }
  } catch (error) {
    showStatus('Erro ao enviar arquivo', 'error');
  }
});

filesList.addEventListener('click', (e) => {
  const button = e.target.closest('button[data-action]');
  if (!button) return;
  if (button.dataset.action === 'download') downloadFile(button.dataset.id);
  if (button.dataset.action === 'delete') deleteFile(button.dataset.id);
});

async function downloadFile(id) {
  try {
    window.location.href = `/api/files/${encodeURIComponent(id)}`;
  } catch (error) {
    showStatus('Erro ao baixar arquivo', 'error');
  }
}

async function deleteFile(id) {
  if (!confirm('Deseja realmente excluir este arquivo?')) {
    return;
  }

  try {
    const response = await fetch(`/api/files/${encodeURIComponent(id)}`, {
      method: 'DELETE'
    });

    const data = await response.json();

    if (data.success) {
      showStatus('Arquivo excluído com sucesso', 'success');
      await loadFiles();
    } else {
      showStatus(data.message || 'Erro ao excluir arquivo', 'error');
    }
  } catch (error) {
    showStatus('Erro ao excluir arquivo', 'error');
  }
}

loadFiles();

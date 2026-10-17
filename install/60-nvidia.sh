# Etapa 60 (opcional): GPU NVIDIA. Driver headless com módulos assinados pela Canonical
# (funciona com Secure Boot, sem DKMS) e NVIDIA Container Toolkit.
# Sem apt-mark hold de propósito: com módulos assinados, travar o driver o separa
# dos módulos do kernel na próxima atualização e quebra a GPU. O apt nunca troca de série sozinho.

[ "$ATENA_GPU" = nvidia ] || return 0

msg "GPU NVIDIA: driver $ATENA_NVIDIA_SERIES e Container Toolkit"

case "$(uname -r)" in
  *-generic) ;;
  *) aviso "kernel $(uname -r) não é o -generic; os módulos assinados podem não existir para ele" ;;
esac

apt-get install -y -qq "nvidia-headless-no-dkms-$ATENA_NVIDIA_SERIES" "nvidia-utils-$ATENA_NVIDIA_SERIES" \
  "linux-modules-nvidia-$ATENA_NVIDIA_SERIES-generic" >/dev/null
ok "driver $(dpkg-query -W -f='${Version}' "nvidia-headless-no-dkms-$ATENA_NVIDIA_SERIES")"

curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
  | gpg --dearmor --yes -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -fsSL https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
  | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
  > /etc/apt/sources.list.d/nvidia-container-toolkit.list
apt-get update -qq
apt-get install -y -qq nvidia-container-toolkit >/dev/null
nvidia-ctk runtime configure --runtime=docker >/dev/null
systemctl restart docker
ok "Container Toolkit: containers podem usar a GPU (gpus: all)"

if ! nvidia-smi >/dev/null 2>&1; then
  REINICIAR=1
  aviso "o driver só carrega depois de reiniciar o servidor"
fi

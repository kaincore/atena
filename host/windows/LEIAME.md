# PC da rede de casa (opcional)

A Atena pode usar um PC com placa de vídeo da sua rede para duas coisas:

- **Modelo maior para texto privado:** `local.processar` com `modelo: "pc"` manda o texto direto ao
  LM Studio do PC, sem nuvem.
- **Ligar e desligar:** `pc.ligar` manda o Wake-on-LAN; `pc.desligar`, `pc.reiniciar` e `pc.cancelar`
  entram no PC por SSH com uma chave que só roda o `atena-pc.ps1` desta pasta.

Tudo é opcional. Sem `ATENA_PC_IP` no `atena.conf`, as ações `pc.*` respondem 404. Sem
`ATENA_PC_USUARIO`, a Atena só liga o PC.

## 1. Ligar pela rede (Wake-on-LAN)

1. Na BIOS, ative **Wake on LAN** (às vezes "Power On By PCI-E").
2. No Windows, em Gerenciador de Dispositivos → placa de rede → Propriedades:
   - aba Avançado: **Wake on Magic Packet** = Ativado;
   - aba Gerenciamento de Energia: marque "Permitir que este dispositivo ative o computador".
3. Desative a inicialização rápida (Opções de Energia → "Escolher a função dos botões de energia").
4. Fixe o IP do PC no roteador e preencha `ATENA_PC_IP` e `ATENA_PC_MAC` no `/etc/atena/atena.conf`
   (o MAC aparece em `ipconfig /all`, "Endereço Físico").

## 2. LM Studio

1. Carregue o modelo (padrão: `qwen3-14b`; outro nome vai em `ATENA_PC_MODELO`).
2. Em Developer, ligue o servidor com **Serve on Local Network**, na porta de `ATENA_PC_PORTA`
   (padrão 1234).
3. No Firewall do Windows, libere essa porta só para o IP do servidor.

Os containers não alcançam a rede de casa (veja `docs/pt/seguranca.md`). Quem fala com o PC é o
executor, que roda no próprio servidor.

## 3. Desligar, reiniciar e cancelar (SSH restrito)

No servidor, o instalador cria a chave da Atena em `/etc/atena/executor/pc-chave`. Mostre a parte
pública:

```bash
sudo cat /etc/atena/executor/pc-chave.pub
```

No PC, abra o PowerShell **como administrador** (a conta precisa ser administradora) e rode, trocando
`IP_DO_SERVIDOR` e `CHAVE_PUBLICA` (a linha inteira que começa com `ssh-ed25519`):

```powershell
# servidor SSH do Windows, só para o servidor da Atena
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
Start-Service sshd
Set-Service -Name sshd -StartupType Automatic
Set-NetFirewallRule -Name OpenSSH-Server-In-TCP -RemoteAddress IP_DO_SERVIDOR -Profile Any

# o script que a chave roda (copie o atena-pc.ps1 desta pasta para o PC antes)
Copy-Item .\atena-pc.ps1 C:\ProgramData\ssh\atena-pc.ps1
icacls C:\ProgramData\ssh\atena-pc.ps1 /inheritance:r /grant "*S-1-5-32-544:F" /grant "*S-1-5-18:F"

# a chave da Atena: só roda o script, sem terminal e sem túneis
$f = "C:\ProgramData\ssh\administrators_authorized_keys"
$linha = 'command="powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File C:\ProgramData\ssh\atena-pc.ps1",no-port-forwarding,no-agent-forwarding,no-x11-forwarding,no-pty CHAVE_PUBLICA'
Add-Content -Path $f -Encoding ascii -Value $linha
icacls $f /inheritance:r /grant "*S-1-5-32-544:F" /grant "*S-1-5-18:F"

# a impressão digital do PC, para conferir no servidor
ssh-keygen -lf C:\ProgramData\ssh\ssh_host_ed25519_key.pub
```

De volta ao servidor, confira se a impressão digital é a mesma que o PC mostrou e só então fixe a
chave do PC (assim ninguém se passa por ele):

```bash
ssh-keyscan -t ed25519 IP_DO_PC 2>/dev/null | ssh-keygen -lf -
ssh-keyscan -t ed25519 IP_DO_PC 2>/dev/null | sudo install -m 644 -o root -g atena-exec /dev/stdin /etc/atena/executor/pc-known-hosts
```

Por fim, ponha o usuário do Windows em `ATENA_PC_USUARIO` no `/etc/atena/atena.conf` (o nome que
aparece em `whoami`, depois da barra). O executor lê o arquivo a cada pedido: não precisa reiniciar.

## Testar

Peça à Atena "o PC está ligado?" (`pc.estado`). Para conferir a trava sem desligar nada:

```bash
sudo -u atena-exec ssh -i /etc/atena/executor/pc-chave -o StrictHostKeyChecking=yes \
  -o UserKnownHostsFile=/etc/atena/executor/pc-known-hosts USUARIO@IP_DO_PC qualquer-coisa
```

A resposta tem que ser `atena-pc: recusado`.

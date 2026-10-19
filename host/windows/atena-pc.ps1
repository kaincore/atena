# Atena: o que o servidor pode pedir a este PC pela chave SSH restrita.
# Instale em C:\ProgramData\ssh\atena-pc.ps1 (veja LEIAME.md nesta pasta).
# So aceita desligar, reiniciar e cancelar; qualquer outra coisa e recusada.
switch ($env:SSH_ORIGINAL_COMMAND) {
  "desligar"  { shutdown.exe /s /t 60 /c "A Atena vai desligar o PC em 60 s. Para cancelar: shutdown /a"; "atena-pc: desligar"; exit $LASTEXITCODE }
  "reiniciar" { shutdown.exe /r /t 60 /c "A Atena vai reiniciar o PC em 60 s. Para cancelar: shutdown /a"; "atena-pc: reiniciar"; exit $LASTEXITCODE }
  "cancelar"  { shutdown.exe /a 2>$null; "atena-pc: cancelar"; exit 0 }
  default     { "atena-pc: recusado"; exit 1 }
}

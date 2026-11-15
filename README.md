# Painel SOC (Windows)

Programa de desktop que mostra, como fluxos de luz, as falhas de login e as conexões de rede do seu próprio Windows.
- Laranja: login que falhou (rosa se forem 5 ou mais em 1 min da mesma origem).
- Azul: conexão nova de rede. Laranja também para conexão incomum (acesso remoto vindo da internet ou portas muito usadas em invasões).
- Fluxos azuis bem fracos de fundo são só decoração.
Só **lê** o registro de segurança e só funciona neste computador. Não altera nada no sistema.

A cena é 3D de verdade (câmera em perspectiva): **arraste com o mouse** para girar; ao soltar, ela volta ao movimento automático.

## Como gerar o instalador no GitHub
1. Entre em github.com e clique em **New** para criar um repositório (ex.: `painel-soc`).
2. Clique em **uploading an existing file** e arraste **todo o conteúdo desta pasta**, incluindo a pasta `.github`.
   Se a `.github` não subir: **Add file > Create new file**, digite `.github/workflows/build.yml` no nome e cole o conteúdo do arquivo.
3. Clique em **Commit changes**.
4. Abra a aba **Actions**, escolha **Gerar instalador do Windows** e clique em **Run workflow**.
5. Espere uns 5 a 10 minutos (bolinha amarela vira ✔ verde).
6. Clique na execução concluída e baixe **PainelSOC-Setup** em *Artifacts* (vem num .zip).
7. Extraia o .zip e dê dois cliques em `PainelSOC-Setup.exe`.

Para publicar na aba **Releases**: crie uma versão chamada `v1.0.0` (Releases > Create a new release).

## Como usar
Abra o **Painel SOC** pelo Menu Iniciar (ele pede permissão de administrador, necessária para ler o log).
Tela cheia: **F11**. Exercício: aperte **Win + L** e erre a senha 5 vezes; depois olhe o painel.

## Se algo falhar
- Aba Actions com ❌: abra a execução, clique na etapa em vermelho e me envie o texto do erro.
- Janela em branco: instale o *WebView2 Runtime* (da Microsoft). Se faltar, o programa abre no navegador.

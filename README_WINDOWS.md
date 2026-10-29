# Radar Startup Intelligence — aplicativo Windows (2.1)

O Radar é um aplicativo **Windows 10/11 (64 bits)**, com janela própria, sem precisar abrir o navegador. O programa usa `pywebview` com **Microsoft Edge WebView2** e mantém o motor de inteligência e coleta Python da versão web local.

## Para utilizar

1. No GitHub, abra **Actions → Radar Windows - testes e instalador** e baixe o artefato de uma execução aprovada.
2. Extraia o ZIP do artefato. Execute `RadarStartupIntelligence-Setup-2.1.0.exe` para instalar, **ou** extraia `RadarStartupIntelligence-Portable.zip` para executar sem instalador.
3. Abra **Radar Startup Intelligence** no menu Iniciar ou pela área de trabalho. Clique em **Atualizar radar** para coletar fontes públicas; é necessária conexão com a internet.
4. Para avaliar com exemplos explicitamente fictícios, a versão de desenvolvimento permite `python desktop.py --demo`; no executável também é possível usar `RadarStartupIntelligence.exe --demo`.

O WebView2 Runtime é necessário e está instalado na maioria dos PCs Windows 11. Caso não esteja disponível, instale-o pelo site oficial da Microsoft: https://developer.microsoft.com/microsoft-edge/webview2/.

## Privacidade e dados

- Os dados reais e as anotações ficam em `%LOCALAPPDATA%\RadarStartupIntelligence\radar.db`. A atualização ou reinstalação do aplicativo não apaga essa pasta.
- Os dados de demonstração ficam **separados** em `radar_demo.db`.
- Para personalizar fontes e setores, crie `%LOCALAPPDATA%\RadarStartupIntelligence\config.yaml` com base no `config.yaml` do repositório.
- Tokens opcionais ficam em `%LOCALAPPDATA%\RadarStartupIntelligence\.env`, **nunca** no repositório ou dentro do instalador.
- Backend HTTP limitado ao loopback `127.0.0.1`, em porta aleatória; janela embutida abre o endereço local.
- Consultas às fontes externas só ocorrem quando a coleta é acionada. O dashboard local não envia suas anotações para um serviço em nuvem.

## Desenvolvimento / execução sem instalador

```powershell
py -m pip install -r requirements-desktop.txt
py desktop.py
py desktop.py --demo
py desktop.py --self-test
```

Para construir o instalador, **o build precisa rodar no Windows**. O workflow `.github/workflows/windows-desktop.yml` instala dependências, roda testes Python, empacota via PyInstaller, verifica o executável e cria o instalador com Inno Setup.

> A aprovação automatizada do build **não equivale** à homologação visual e funcional em um computador real. Validar abertura da janela, WebView2, rede, coleta, exportação CSV/JSON e instalação/desinstalação em Windows 10/11 antes de uma distribuição pública.

# Setvo — Inteligência de Mercado (Windows 2.2)

O Setvo é um aplicativo **Windows 10/11 (64 bits)**, com janela própria, sem precisar abrir o navegador. O programa usa `pywebview` com **Microsoft Edge WebView2** e mantém o motor de inteligência e coleta Python da versão web local.

## Para utilizar

1. No GitHub, abra **Actions → Setvo Windows - testes e instalador** e baixe o artefato de uma execução aprovada.
2. Extraia o ZIP do artefato. Execute `Setvo-Setup-2.2.0.exe` para instalar, **ou** extraia `Setvo-Portable.zip` para executar sem instalador.
3. Abra **Setvo** no menu Iniciar ou pela área de trabalho. Clique em **Atualizar dados** para coletar fontes públicas; é necessária conexão com a internet.
4. Para avaliar com exemplos explicitamente fictícios, a versão de desenvolvimento permite `python desktop.py --demo`; no executável também é possível usar `Setvo.exe --demo`.

Esta versão substitui o **conceito** do Setvo assistente Windows: agora é dedicada à pesquisa de tendências, problemas e oportunidades de startups. Não contém comandos de voz ou automação do computador.

O WebView2 Runtime é necessário e está instalado na maioria dos PCs Windows 11. Caso não esteja disponível, instale-o pelo site oficial da Microsoft: https://developer.microsoft.com/microsoft-edge/webview2/.

## Privacidade e dados

- Os dados Radar 2.1 existentes são copiados uma vez, sem apagar a pasta original. Os dados reais e as anotações ficam em `%LOCALAPPDATA%\SetvoIntelligence\radar.db`. A atualização ou reinstalação do aplicativo não apaga essa pasta.
- Os dados de demonstração ficam **separados** em `radar_demo.db`.
- Para personalizar fontes e setores, crie `%LOCALAPPDATA%\SetvoIntelligence\config.yaml` com base no `config.yaml` do repositório.
- Tokens opcionais ficam em `%LOCALAPPDATA%\SetvoIntelligence\.env`, **nunca** no repositório ou dentro do instalador.
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

## Aviso de download perigoso / SmartScreen

O instalador gerado automaticamente no modo normal e **PREVIEW NAO ASSINADA**. Isso pode causar alertas do Edge, Chrome ou SmartScreen, mesmo sem deteccao de malware. Nao desative antivirus nem SmartScreen para instalar. Consulte [SECURITY_DOWNLOADS.md](SECURITY_DOWNLOADS.md) para verificar origem, hashes SHA-256, estado da assinatura e procedimento de assinatura do publicador. Quando existir identidade verificada e conta de Microsoft Artifact Signing configurada, um build manual permite `assinar=true`; a assinatura nao garante reputacao imediata. Se o antivirus identificar uma ameaca especifica, nao execute o arquivo ate investigar.

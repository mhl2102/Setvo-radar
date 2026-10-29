# Setvo — Integridade de downloads e aviso do SmartScreen

**Aviso importante:** O instalador Setvo Windows de preview e gerado sem uma assinatura Authenticode de um publicador verificado. O aviso `aplicativo desconhecido` ou `nao e baixado com frequencia` pode ser reputacao insuficiente, nao prova de malware. Se houver uma **deteccao especifica de virus/trojan**, interrompa o uso e investigue; nao a contorne.

## Melhorias de verificacao do build

- PyInstaller com `--noupx` para nao compactar arquivos executaveis com UPX.
- Testes automatizados e teste funcional `Setvo.exe --self-test`.
- Se Microsoft Defender estiver ativo no runner, tentativa de exame no executavel e instalador. A ausencia do Defender fica explicita no arquivo `ANTIVIRUS_SCAN.txt` — o workflow **nao** declara que um arquivo foi examinado quando nao foi.
- Hashes SHA-256 em `SHA256SUMS.txt`, gerados **depois** da compilacao e eventual assinatura.
- Status Authenticode em `ASSINATURA_STATUS.txt`.
- Artefato de preview com nome `PREVIEW-NAO-ASSINADO`; nao representar o teste como publicacao assinada.

## Como verificar um download

1. Baixe da pagina de execucao aprovada em [Actions do repositorio](https://github.com/mhl2102/Setvo-radar/actions/workflows/windows-desktop.yml), nunca de reuploads desconhecidos.
2. Baixe o artefato **SETVO-INSTALADOR-PREVIEW-NAO-ASSINADO**; ele contem o instalador sem outro ZIP interno. Extraia o ZIP antes de executar. Dentro do artefato, encontre `SHA256SUMS.txt` e o instalador.
3. Abra PowerShell na pasta do instalador e execute `Get-FileHash .\Setvo-Setup-2.3.1.exe -Algorithm SHA256` (adapte o nome se mudar). Compare o resultado com `SHA256SUMS.txt`. Isso detecta adulteracao **em relacao ao manifesto**, mas nao comprova ausencia de malware.
4. Consulte `ASSINATURA_STATUS.txt`. Uma preview sem assinatura continua sujeita a avisos; **nao ignore uma deteccao de malware**.
5. Se o arquivo for bloqueado como malicioso, registre a mensagem/ID da deteccao e encaminhe o arquivo para analise de seguranca; nao reduza as protecoes do Windows.

## Publicacao assinada (requer configuracao pelo responsavel)

Para assinar oficialmente o executavel e o instalador, configure uma identidade e um perfil de certificado valido e a integracao [Microsoft Artifact Signing](https://learn.microsoft.com/pt-br/azure/artifact-signing/quickstart).

> Verifique se a conta e a modalidade de certificado sao elegiveis para sua localizacao. Regiao do servidor Azure nao implica elegibilidade de pessoas ou empresas do Brasil. Alternativa: certificado de assinatura de codigo emitido por autoridade confiavel, com processo separado de assinatura.

No GitHub, configure as credenciais **apenas em Settings > Secrets and variables > Actions**:

- Secrets: `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, com federacao OIDC na assinatura Azure.
- Variables: `AZURE_SIGNING_ENDPOINT`, `AZURE_SIGNING_ACCOUNT`, `AZURE_CERTIFICATE_PROFILE`.

Apos aprovacoes de identidade e configuracao, execute manualmente o workflow **Setvo Windows - testes e instalador**, com a opcao `assinar`. O workflow falha se a assinatura nao for valida. Nao coloque chaves privadas, senhas, tokens ou certificados de assinatura no chat, no codigo ou em commits.

**Limitacao atual:** O Inno Setup e compilado sem `SignTool` configurado; assinar o instalador apos a compilacao nao assina automaticamente o desinstalador e copias temporarias internas. Para distribuicao comercial, integrar assinatura tambem ao processo Inno Setup (SignTool + SignedUninstaller), ou adotar pacote de distribuicao assinado, como o disponibilizado pela Microsoft Store.

Mesmo um `.exe` assinado pode apresentar SmartScreen enquanto nao construir reputacao. A publicacao pela Microsoft Store e a alternativa mais confiavel para reduzir esses avisos.

Referencias:
- https://learn.microsoft.com/pt-br/windows/apps/package-and-deploy/smartscreen-reputation
- https://learn.microsoft.com/pt-br/azure/artifact-signing/quickstart
- https://github.com/Azure/artifact-signing-action

## Evitar erro python312.dll

Os downloads sao publicados em dois artefatos distintos: **SETVO-INSTALADOR** (recomendado) e **SETVO-PORTATIL-EXTRAIR-TUDO**. Ambos chegam em um unico ZIP disponibilizado pelo GitHub. Extraia o ZIP inteiro antes de executar. No portatil, mantenha `Setvo.exe` e `_internal/python312.dll` juntos na pasta extraida. O processo de compilacao valida a DLL e simula a extracao antes de publicar. O erro pode ter outras causas (quarentena do antivirus, arquivos corrompidos, dependencias do Windows); nao ignore alertas de malware.

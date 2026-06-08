# Prova de Conceito HE

## Arquitetura

```
[CLIENTE]                    [AWS S3]                   [SERVIDOR]
  │                              │                           │
  ├─ Gera chaves BFV             │                           │
  ├─ Criptografa dados ─────────►│ ciphertext.bin            │
  ├─ Envia contexto público ────►│ context_public.bin        │
  │                              │◄── baixa arquivos ────────┤
  │                              │                           ├─ Processa (cifrado)
  │                              │◄── result.bin ────────────┤
  ├─ Baixa resultado ◄───────────│                           │
  └─ Descriptografa              │                           │
```

**A chave secreta nunca sai do container do cliente.**

## Pré-requisitos

- Docker + Docker Compose instalados
- Bucket S3 na AWS criado
- Usuário IAM com permissões `s3:GetObject`, `s3:PutObject`, `s3:HeadObject`

## Configuração

1. Edite o arquivo `.env` com suas credenciais:

```env
AWS_ACCESS_KEY_ID=SUA_ACCESS_KEY_AQUI
AWS_SECRET_ACCESS_KEY=SUA_SECRET_KEY_AQUI
AWS_DEFAULT_REGION=us-east-1
S3_BUCKET_NAME=nome-do-seu-bucket
```

2. Construa e execute:

```bash
docker-compose up --build
```

## Estrutura de arquivos

```
healthdata/
├── docker-compose.yml
├── .env                  ← suas credenciais (não commitar!)
├── client/
│   ├── Dockerfile
│   └── client.py
└── server/
    ├── Dockerfile
    └── server.py
```

## Objetos no S3

| Chave S3 | Descrição |
|---|---|
| `healthdata/ciphertext.bin` | Dados dos pacientes cifrados |
| `healthdata/context_public.bin` | Contexto público BFV (sem chave secreta) |
| `healthdata/result.bin` | Resultado homomórfico cifrado |

## Biblioteca utilizada

**TenSEAL** com esquema **BFV (Brakerski/Fan-Vercauteren)**  
- Adequado para operações em inteiros  
- Construído sobre Microsoft SEAL  
- `poly_modulus_degree=4096`, `plain_modulus=1032193`

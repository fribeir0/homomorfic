"""
HealthData Analytics S.A. - CLIENTE
Responsável por:
  - Gerar chaves homomórficas (BFV via TenSEAL)
  - Criptografar dados inteiros dos pacientes
  - Fazer upload dos dados criptografados para S3 (AWS real)
  - Baixar o resultado processado e descriptografar
A chave secreta NUNCA sai deste container.
"""

import os
import json
import time
import tenseal as ts
import boto3
from pathlib import Path

# ──────────────────────────────────────────────
# Configurações
# ──────────────────────────────────────────────
BUCKET   = os.environ["S3_BUCKET_NAME"]
REGION   = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
KEY_DIR  = Path("/app/keys")
DATA_DIR = Path("/app/data")

KEY_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Dados simulados de pacientes (números inteiros: ex. frequência cardíaca, glicemia)
PATIENT_DATA = [72, 85, 90, 110, 78, 95, 88, 102, 76, 83]


def get_s3():
    return boto3.client(
        "s3",
        region_name=REGION,
        aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
    )


def generate_keys():
    """Gera contexto BFV e salva chave pública (compartilhada) e secreta (local)."""
    print("[CLIENTE] Gerando par de chaves BFV...")
    ctx = ts.context(
        ts.SCHEME_TYPE.BFV,
        poly_modulus_degree=4096,
        plain_modulus=1032193,
    )
    ctx.generate_galois_keys()
    ctx.generate_relin_keys()

    # Chave pública – pode ser compartilhada
    public_ctx_bytes = ctx.serialize(save_secret_key=False)
    # Chave secreta – fica apenas no cliente
    secret_ctx_bytes = ctx.serialize(save_secret_key=True)

    (KEY_DIR / "context_public.bin").write_bytes(public_ctx_bytes)
    (KEY_DIR / "context_secret.bin").write_bytes(secret_ctx_bytes)
    print("[CLIENTE] Chaves geradas. Chave secreta armazenada LOCALMENTE.")
    return ctx


def encrypt_data(ctx):
    """Criptografa os dados dos pacientes com BFV."""
    print(f"[CLIENTE] Criptografando {len(PATIENT_DATA)} valores...")
    enc = ts.bfv_vector(ctx, PATIENT_DATA)
    ct_bytes = enc.serialize()
    (DATA_DIR / "ciphertext.bin").write_bytes(ct_bytes)
    print(f"[CLIENTE] Dados originais    : {PATIENT_DATA}")
    print(f"[CLIENTE] Tamanho cifrado    : {len(ct_bytes)} bytes")
    return ct_bytes


def upload_to_s3(s3, ct_bytes, public_ctx_bytes):
    """Envia texto cifrado e contexto público para o bucket S3."""
    print(f"[CLIENTE] Fazendo upload para S3 bucket '{BUCKET}'...")
    s3.put_object(Bucket=BUCKET, Key="healthdata/ciphertext.bin",      Body=ct_bytes)
    s3.put_object(Bucket=BUCKET, Key="healthdata/context_public.bin",  Body=public_ctx_bytes)
    print("[CLIENTE] Upload concluído: ciphertext.bin + context_public.bin")


def wait_for_result(s3, timeout=120, interval=5):
    """Aguarda o servidor depositar o resultado no S3."""
    print(f"[CLIENTE] Aguardando resultado do servidor (timeout={timeout}s)...")
    elapsed = 0
    while elapsed < timeout:
        try:
            s3.head_object(Bucket=BUCKET, Key="healthdata/result.bin")
            print("[CLIENTE] Resultado encontrado no S3!")
            return True
        except s3.exceptions.ClientError:
            pass
        except Exception:
            pass
        time.sleep(interval)
        elapsed += interval
        print(f"[CLIENTE]   ... aguardando ({elapsed}s)")
    return False


def download_and_decrypt(s3):
    """Baixa o resultado e descriptografa com a chave secreta."""
    resp = s3.get_object(Bucket=BUCKET, Key="healthdata/result.bin")
    result_bytes = resp["Body"].read()
    (DATA_DIR / "result.bin").write_bytes(result_bytes)

    # Carrega contexto com chave secreta (somente no cliente)
    secret_ctx = ts.context_from(
        (KEY_DIR / "context_secret.bin").read_bytes()
    )
    result_vec = ts.bfv_vector_from(secret_ctx, result_bytes)
    decrypted = result_vec.decrypt()
    return decrypted


def main():
    print("=" * 55)
    print("  HealthData Analytics S.A. — CLIENTE HOMOMÓRFICO")
    print("=" * 55)

    # 1. Gerar chaves
    ctx = generate_keys()

    # 2. Criptografar dados
    ct_bytes        = encrypt_data(ctx)
    public_ctx_bytes = (KEY_DIR / "context_public.bin").read_bytes()

    # 3. Upload para S3
    s3 = get_s3()
    upload_to_s3(s3, ct_bytes, public_ctx_bytes)

    # 4. Aguardar servidor processar
    found = wait_for_result(s3)
    if not found:
        print("[CLIENTE] ERRO: timeout aguardando resultado do servidor.")
        return

    # 5. Baixar e descriptografar resultado
    decrypted = download_and_decrypt(s3)

    # 6. Verificação local
    expected_sum   = sum(PATIENT_DATA)
    expected_sq    = [v * v for v in PATIENT_DATA]

    print()
    print("=" * 55)
    print("  RESULTADOS")
    print("=" * 55)
    print(f"  Dados originais   : {PATIENT_DATA}")
    print(f"  Soma esperada     : {expected_sum}")
    print(f"  Soma descriptogr. : {decrypted[0]}")  # primeiro elemento = soma total
    print(f"  Correspondência   : {'✅ SIM' if decrypted[0] == expected_sum else '❌ NÃO'}")
    print("=" * 55)

    # Salva log
    log = {
        "dados_originais": PATIENT_DATA,
        "soma_esperada": expected_sum,
        "soma_descriptografada": decrypted[0],
        "ok": decrypted[0] == expected_sum,
    }
    (DATA_DIR / "resultado_final.json").write_text(json.dumps(log, indent=2))
    print("[CLIENTE] Log salvo em /app/data/resultado_final.json")


if __name__ == "__main__":
    main()

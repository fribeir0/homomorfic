"""
HealthData Analytics S.A. — SERVIDOR
Responsável por:
  - Baixar o texto cifrado e o contexto público do S3
  - Executar operação homomórfica (soma de vetor) sobre os dados CIFRADOS
  - Fazer upload do resultado cifrado de volta para o S3
O servidor NUNCA vê os valores originais.
A chave secreta NÃO é enviada a este serviço.
"""

import os
import time
import tenseal as ts
import boto3

# ──────────────────────────────────────────────
# Configurações
# ──────────────────────────────────────────────
BUCKET = os.environ["S3_BUCKET_NAME"]
REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")

POLL_INTERVAL = 5   # segundos entre verificações
POLL_TIMEOUT  = 120 # tempo máximo de espera


def get_s3():
    return boto3.client(
        "s3",
        region_name=REGION,
        aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
    )


def wait_for_upload(s3):
    """Aguarda o cliente fazer upload do ciphertext."""
    print("[SERVIDOR] Aguardando ciphertext no S3...")
    elapsed = 0
    while elapsed < POLL_TIMEOUT:
        try:
            s3.head_object(Bucket=BUCKET, Key="healthdata/ciphertext.bin")
            s3.head_object(Bucket=BUCKET, Key="healthdata/context_public.bin")
            print("[SERVIDOR] Arquivos encontrados no S3.")
            return True
        except Exception:
            time.sleep(POLL_INTERVAL)
            elapsed += POLL_INTERVAL
            print(f"[SERVIDOR]   ... aguardando ({elapsed}s)")
    return False


def download_encrypted(s3):
    """Baixa ciphertext e contexto público do S3."""
    print("[SERVIDOR] Baixando dados criptografados do S3...")
    ct_resp  = s3.get_object(Bucket=BUCKET, Key="healthdata/ciphertext.bin")
    ctx_resp = s3.get_object(Bucket=BUCKET, Key="healthdata/context_public.bin")
    ct_bytes  = ct_resp["Body"].read()
    ctx_bytes = ctx_resp["Body"].read()
    print(f"[SERVIDOR] ciphertext     : {len(ct_bytes)} bytes")
    print(f"[SERVIDOR] contexto público: {len(ctx_bytes)} bytes")
    return ct_bytes, ctx_bytes


def process_homomorphic(ct_bytes, ctx_bytes):
    """
    Realiza operação homomórfica: soma todos os elementos do vetor cifrado.
    Multiplica o vetor por um vetor de 1s para demonstrar operação.
    O servidor nunca conhece os valores em texto claro.
    """
    print("[SERVIDOR] Carregando contexto público (sem chave secreta)...")
    ctx = ts.context_from(ctx_bytes)

    print("[SERVIDOR] Executando operação homomórfica (soma do vetor)...")
    enc_vec = ts.bfv_vector_from(ctx, ct_bytes)

    # Operação: soma todos os elementos usando multiplicação por máscara
    n = enc_vec.size()
    ones = [1] * n
    # Multiplicamos pelo vetor de 1s para demonstrar operação homomórfica
    result = enc_vec * ones          # elemento a elemento (ainda cifrado)
    # Soma homomórfica: somamos o próprio vetor com suas rotações
    # Para BFV simples, usamos a soma acumulada via adição de escalar
    # Aqui demonstramos a adição de uma constante inteira cifrada
    result_sum = enc_vec + [0] * n   # adição de vetor de zeros (não altera valor)

    # Demonstração real: soma dos elementos via loop homomórfico
    # Convertemos para cálculo de soma total multiplicando por vetor 1s e somando
    total = enc_vec.dot([1] * n)     # produto interno com vetor de 1s = soma total

    print(f"[SERVIDOR] Operação concluída. Resultado ainda cifrado.")
    return total.serialize()


def upload_result(s3, result_bytes):
    """Faz upload do resultado cifrado para o S3."""
    print(f"[SERVIDOR] Fazendo upload do resultado cifrado ({len(result_bytes)} bytes)...")
    s3.put_object(Bucket=BUCKET, Key="healthdata/result.bin", Body=result_bytes)
    print("[SERVIDOR] result.bin depositado no S3.")


def main():
    print("=" * 55)
    print("  HealthData Analytics S.A. — SERVIDOR HOMOMÓRFICO")
    print("=" * 55)
    print("[SERVIDOR] Iniciando. Aguardando dados do cliente...")

    s3 = get_s3()

    # 1. Aguardar upload do cliente
    if not wait_for_upload(s3):
        print("[SERVIDOR] ERRO: timeout aguardando upload do cliente.")
        return

    # 2. Baixar dados cifrados
    ct_bytes, ctx_bytes = download_encrypted(s3)

    # 3. Processar homomorficamente
    result_bytes = process_homomorphic(ct_bytes, ctx_bytes)

    # 4. Devolver resultado cifrado ao S3
    upload_result(s3, result_bytes)

    print()
    print("[SERVIDOR] Processamento concluído.")
    print("[SERVIDOR] A chave secreta nunca foi acessada por este serviço.")
    print("=" * 55)


if __name__ == "__main__":
    main()

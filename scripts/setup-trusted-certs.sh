#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

CERTS_DIR="dovecot/certs"
CA_KEY="$CERTS_DIR/ca.key"
CA_CERT="$CERTS_DIR/ca.pem"
SERVER_KEY="$CERTS_DIR/server.key"
SERVER_CSR="$CERTS_DIR/server.csr"
SERVER_CERT="$CERTS_DIR/server.pem"
SERVER_EXT="$CERTS_DIR/server.ext"

if ! command -v openssl >/dev/null 2>&1; then
    echo "openssl is required to create sandbox IMAP TLS certificates." >&2
    exit 1
fi

mkdir -p "$CERTS_DIR"

if [ "${FORCE:-}" != "1" ] \
    && [ -f "$CA_CERT" ] \
    && [ -f "$CA_KEY" ] \
    && [ -f "$SERVER_CERT" ] \
    && [ -f "$SERVER_KEY" ]; then
    echo "Sandbox IMAP TLS certificates already exist in $CERTS_DIR."
    exit 0
fi

echo "Creating sandbox IMAP TLS certificates in $CERTS_DIR..."

openssl genrsa -out "$CA_KEY" 4096 >/dev/null 2>&1
openssl req -x509 -new -nodes \
    -key "$CA_KEY" \
    -sha256 \
    -days 3650 \
    -subj "/CN=MailSubsystem Sandbox CA" \
    -out "$CA_CERT" >/dev/null 2>&1

openssl genrsa -out "$SERVER_KEY" 2048 >/dev/null 2>&1
openssl req -new \
    -key "$SERVER_KEY" \
    -subj "/CN=localhost" \
    -out "$SERVER_CSR" >/dev/null 2>&1

cat >"$SERVER_EXT" <<'EOF'
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage=digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth
subjectAltName=@alt_names

[alt_names]
DNS.1=localhost
IP.1=127.0.0.1
IP.2=::1
EOF

openssl x509 -req \
    -in "$SERVER_CSR" \
    -CA "$CA_CERT" \
    -CAkey "$CA_KEY" \
    -CAcreateserial \
    -out "$SERVER_CERT" \
    -days 825 \
    -sha256 \
    -extfile "$SERVER_EXT" >/dev/null 2>&1

rm -f "$SERVER_CSR" "$SERVER_EXT" "$CERTS_DIR/ca.srl"
chmod 600 "$CA_KEY" "$SERVER_KEY"
chmod 644 "$CA_CERT" "$SERVER_CERT"

echo "Sandbox certificates are ready."
echo "  Dovecot cert: $SERVER_CERT"
echo "  Trust bundle: $CA_CERT"

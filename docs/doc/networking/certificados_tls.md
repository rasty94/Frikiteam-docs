---
title: Certificados TLS
description: Tipos de validación (DV, OV, EV), cadenas de confianza y buenas prácticas de configuración.
draft: false
updated: 2026-01-25
difficulty: intermediate
estimated_time: 6 min
category: Redes
status: published
last_reviewed: 2026-01-25
prerequisites:
  - "Conocimientos básicos de DevOps"
  - "Fundamentos de redes"
reviewers: ["@rasty94"]
contributors: ["@rasty94"]
---

# Certificados TLS

Los certificados TLS (Transport Layer Security) son fundamentales para la seguridad de las comunicaciones web. Este documento cubre los tipos de validación, gestión de cadenas de confianza y mejores prácticas de configuración.

## Conceptos Básicos de TLS

### ¿Qué es un Certificado TLS?

Un certificado TLS es un documento digital que vincula una clave pública con una identidad (dominio, organización). Permite establecer conexiones HTTPS seguras mediante cifrado asimétrico.

### Componentos de un Certificado

- **Subject:** Identidad del titular (CN, O, OU, etc.)
- **Issuer:** Autoridad certificadora (CA)
- **Validity Period:** Fechas de validez
- **Public Key:** Clave pública para cifrado
- **Signature:** Firma digital de la CA
- **Extensions:** Información adicional (SAN, etc.)

## Tipos de Validación

### DV (Domain Validation)

#### Características
- **Validación:** Solo propiedad del dominio
- **Proceso:** Email, HTTP-01, DNS-01 challenge
- **Tiempo:** Minutos a horas
- **Costo:** Bajo (gratuito con Let's Encrypt)
- **Indicador:** Candado verde en navegador

#### Proceso de Emisión
1. **Solicitud:** Generar CSR con dominio
2. **Challenge:** CA envía token para verificar
3. **Validación:** Probar acceso al dominio
4. **Emisión:** Certificado firmado

#### Ejemplo con Certbot
```bash
# DV con Let's Encrypt
certbot certonly --webroot -w /var/www/html -d example.com

# Con DNS challenge
certbot certonly --dns-cloudflare -d example.com
```

### OV (Organization Validation)

#### Características
- **Validación:** Propiedad del dominio + identidad de organización
- **Proceso:** Verificación de documentos legales
- **Tiempo:** Días a semanas
- **Costo:** Medio-alto
- **Indicador:** Candado verde + "Empresa verificada"

#### Requisitos de Validación
- **Dominio:** Propiedad verificada
- **Organización:** Registro comercial válido
- **Autoridad:** Persona autorizada para firmar
- **Dirección:** Verificación física

### EV (Extended Validation)

#### Características
- **Validación:** Verificación exhaustiva de identidad
- **Proceso:** Auditoría completa de la organización
- **Tiempo:** Semanas
- **Costo:** Alto
- **Indicador:** Candado verde + barra de dirección verde

#### Beneficios EV
- **Confianza:** Máxima confianza del usuario
- **Protección:** Contra phishing avanzado
- **SEO:** Potencial boost en rankings

## Cadenas de Certificado

### Estructura de la Cadena

```
Root CA
├── Intermediate CA 1
│   ├── Intermediate CA 2
│   │   └── Server Certificate
│   └── Server Certificate
└── Server Certificate
```

### Tipos de Certificados en la Cadena

#### Root Certificate
- **Emisor:** Auto-firmado
- **Almacenamiento:** En trust stores del sistema
- **Validez:** Larga (10-30 años)
- **Uso:** Firma de intermediate CAs

#### Intermediate Certificate
- **Emisor:** Root CA
- **Propósito:** Firma de server certificates
- **Cadena:** Múltiples niveles posibles
- **Rotación:** Periódica

#### Server Certificate (Leaf)
- **Emisor:** Intermediate CA
- **Dominio:** El sitio web
- **Validez:** 90 días (Let's Encrypt) a 2 años
- **SAN:** Múltiples dominios/subdominios

### Configuración de Cadena Completa

#### En Apache
```apache
SSLCertificateFile /etc/ssl/certs/example.com.crt
SSLCertificateKeyFile /etc/ssl/private/example.com.key
SSLCertificateChainFile /etc/ssl/certs/intermediate.crt
```

#### En Nginx
```nginx
server {
    listen 443 ssl http2;
    server_name example.com;
    
    ssl_certificate /etc/ssl/certs/fullchain.pem;
    ssl_certificate_key /etc/ssl/private/example.com.key;
    ssl_trusted_certificate /etc/ssl/certs/chain.pem;
}
```

#### Verificar Cadena
```bash
# Ver contenido del certificado
openssl x509 -in example.com.crt -text -noout

# Verificar cadena
openssl verify -CAfile chain.pem example.com.crt

# Probar conexión SSL
openssl s_client -connect example.com:443 -servername example.com
```

## Gestión de Certificados

### Generación de CSR

```bash
# Generar clave privada
openssl genrsa -out example.com.key 2048

# Crear CSR
openssl req -new -key example.com.key -out example.com.csr \
  -subj "/C=ES/ST=Madrid/L=Madrid/O=Example Corp/CN=example.com"

# Con SAN (Subject Alternative Names)
cat > san.cnf << EOF
[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no

[req_distinguished_name]
C = ES
ST = Madrid
L = Madrid
O = Example Corp
CN = example.com

[v3_req]
keyUsage = keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = example.com
DNS.2 = www.example.com
DNS.3 = api.example.com
EOF

openssl req -new -key example.com.key -out example.com.csr -config san.cnf
```

### Renovación Automática

#### Con Certbot
```bash
# Configurar renovación automática
certbot renew --dry-run

# Hook post-renovación
certbot certonly --webroot -w /var/www/html -d example.com \
  --post-hook "systemctl reload nginx"
```

#### Script Personalizado
```bash
#!/bin/bash
# Verificar expiración y renovar

DOMAIN="example.com"
DAYS_WARNING=30

# Calcular días hasta expiración
EXPIRY=$(openssl x509 -enddate -noout -in /etc/ssl/certs/$DOMAIN.crt | cut -d= -f2)
EXPIRY_SECONDS=$(date -d "$EXPIRY" +%s)
NOW_SECONDS=$(date +%s)
DAYS_LEFT=$(( ($EXPIRY_SECONDS - $NOW_SECONDS) / 86400 ))

if [ $DAYS_LEFT -lt $DAYS_WARNING ]; then
    echo "Certificado expira en $DAYS_LEFT días. Renovando..."
    certbot renew --cert-name $DOMAIN
    systemctl reload nginx
fi
```

## Configuraciones Seguras

### Cipher Suites Recomendadas

#### Moderno (Recomendado)
```nginx
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384;
ssl_prefer_server_ciphers off;
```

#### Intermedio
```nginx
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES128-GCM-SHA256;
```

#### Compatibilidad Antigua (No recomendado)
```nginx
ssl_protocols TLSv1 TLSv1.1 TLSv1.2;
ssl_ciphers HIGH:!aNULL:!MD5;
```

### OCSP Stapling

```nginx
ssl_stapling on;
ssl_stapling_verify on;
ssl_trusted_certificate /etc/ssl/certs/chain.pem;

resolver 8.8.8.8 8.8.4.4 valid=300s;
resolver_timeout 5s;
```

### HSTS (HTTP Strict Transport Security)

```nginx
add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
```

### HPKP (Public Key Pinning) - DEPRECATED

**Nota:** HPKP está obsoleto. Usar Certificate Transparency en su lugar.

## Monitoreo y Alertas

### Verificación de Certificados

```bash
# Verificar expiración
openssl x509 -enddate -noout -in cert.pem

# Verificar con servidor remoto
echo | openssl s_client -servername example.com -connect example.com:443 2>/dev/null | openssl x509 -noout -dates

# SSL Labs test
curl -s "https://api.ssllabs.com/api/v3/analyze?host=example.com" | jq '.endpoints[0].grade'
```

### Scripts de Monitoreo

```python
import ssl
import socket
from datetime import datetime

def check_ssl_cert(hostname, port=443):
    context = ssl.create_default_context()
    conn = context.wrap_socket(socket.socket(), server_hostname=hostname)
    conn.connect((hostname, port))
    
    cert = conn.getpeercert()
    conn.close()
    
    # Extraer fechas
    not_before = datetime.strptime(cert['notBefore'], '%b %d %H:%M:%S %Y %Z')
    not_after = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
    
    days_left = (not_after - datetime.now()).days
    
    return {
        'subject': cert['subject'],
        'issuer': cert['issuer'],
        'not_before': not_before,
        'not_after': not_after,
        'days_left': days_left,
        'valid': days_left > 0
    }

# Uso
cert_info = check_ssl_cert('example.com')
print(f"Certificado válido por {cert_info['days_left']} días")
```

### Alertas con Nagios/Icinga

```bash
# Comando check_ssl_cert
/usr/lib/nagios/plugins/check_ssl_cert -H example.com -w 30 -c 7
```

## Problemas Comunes y Soluciones

### 1. Certificate Chain Issues

**Error:** `unable to get local issuer certificate`

**Solución:** Incluir intermediate certificates en la configuración

### 2. Mismatched Domain

**Error:** `Certificate verification error`

**Solución:** Verificar que CN o SAN coincida con el dominio

### 3. Expired Certificate

**Error:** `certificate verify failed`

**Solución:** Renovar certificado antes de expiración

### 4. Weak Cipher Suites

**Error:** Vulnerabilidades SSL/TLS

**Solución:** Configurar cipher suites modernas

## Certificate Transparency

### ¿Qué es CT?

Certificate Transparency es un framework para monitorizar y auditar certificados SSL/TLS emitidos por CAs.

### SCT (Signed Certificate Timestamp)

Los certificados incluyen SCTs para probar que fueron registrados en logs públicos de CT.

### Verificación CT

```bash
# Ver SCTs en certificado
openssl x509 -in cert.pem -text | grep -A 5 "CT Precertificate SCTs"

# Verificar con crt.sh
curl "https://crt.sh/?q=example.com&output=json"
```

## Mejores Prácticas

### Gestión
1. **Automatización:** Usar ACME (Let's Encrypt) para DV
2. **Monitoreo:** Alertas de expiración
3. **Backup:** Copias de claves privadas seguras
4. **Rotación:** Renovar antes de expirar

### Seguridad
1. **Claves fuertes:** Mínimo 2048 bits RSA, preferir ECDSA
2. **SAN:** Usar Subject Alternative Names
3. **HSTS:** Implementar HTTP Strict Transport Security
4. **OCSP:** Configurar OCSP Stapling

### Rendimiento
1. **Session resumption:** TLS session tickets
2. **OCSP stapling:** Evitar consultas OCSP
3. **CDN:** Usar CDN con certificados gestionados

## Referencias

- RFC 5246: The Transport Layer Security (TLS) Protocol Version 1.2
- RFC 8446: The Transport Layer Security (TLS) Protocol Version 1.3
- RFC 5280: Internet X.509 Public Key Infrastructure Certificate and Certificate Revocation List (CRL) Profile
- RFC 6962: Certificate Transparency
- CA/Browser Forum Baseline Requirements
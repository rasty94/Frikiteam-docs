---
title: SPF/DKIM/DMARC
description: Tríada de seguridad del correo electrónico para prevenir spoofing y asegurar la entregabilidad.
draft: false
---

# SPF/DKIM/DMARC

SPF, DKIM y DMARC forman la tríada esencial de autenticación de email, protegiendo contra spoofing y mejorando la entregabilidad del correo electrónico.

## SPF (Sender Policy Framework)

### ¿Qué es SPF?

SPF es un protocolo que permite verificar si un servidor de email está autorizado para enviar correo en nombre de un dominio.

### Cómo Funciona

1. **Publicación:** El dominio publica IPs/servidores autorizados
2. **Verificación:** El receptor consulta el registro SPF del dominio remitente
3. **Validación:** Compara la IP del servidor con la lista autorizada

### Sintaxis del Registro SPF

```
v=spf1 [mecanismos] [modificadores]
```

#### Mecanismos Principales

| Mecanismo | Descripción | Ejemplo |
|-----------|-------------|---------|
| `+ip4:` | IP IPv4 autorizada | `+ip4:192.168.1.1` |
| `+ip6:` | IP IPv6 autorizada | `+ip6:2001:db8::1` |
| `+a` | Autoriza A/AAAA records | `+a:mail.example.com` |
| `+mx` | Autoriza registros MX | `+mx` |
| `+include:` | Incluye política de otro dominio | `+include:_spf.google.com` |
| `+all` | Permite todo (no recomendado) | `+all` |
| `-all` | Niega todo lo demás | `-all` |
| `~all` | Soft fail (recomendado) | `~all` |

#### Ejemplos de Registros SPF

**Básico para dominio propio:**
```
v=spf1 +mx +a:mail.example.com -all
```

**Con servicios externos:**
```
v=spf1 include:_spf.google.com include:spf.protection.outlook.com -all
```

**Para mailing lists:**
```
v=spf1 include:_spf.google.com include:servers.mcsv.net ~all
```

### Configuración SPF

#### En BIND/DNS
```bind
@ IN TXT "v=spf1 +mx +a:mail.example.com -all"
```

#### Verificación
```bash
# Verificar registro SPF
dig TXT example.com

# Probar SPF
spfquery -ip=192.168.1.1 -sender=user@example.com
```

## DKIM (DomainKeys Identified Mail)

### ¿Qué es DKIM?

DKIM firma criptográficamente los emails salientes, permitiendo verificar que el contenido no ha sido alterado y confirmar la autenticidad del remitente.

### Cómo Funciona DKIM

1. **Generación de claves:** El dominio crea par de claves público/privado
2. **Firma:** El MTA firma el email con la clave privada
3. **Publicación:** La clave pública se publica en DNS
4. **Verificación:** El receptor verifica la firma con la clave pública

### Componentes DKIM

#### Selector
Identifica qué clave usar cuando hay múltiples:

```
selector._domainkey.example.com
```

#### Registro DKIM
```bind
selector._domainkey IN TXT "v=DKIM1; k=rsa; p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQC..."
```

#### Cabecera DKIM-Signature
```
DKIM-Signature: v=1; a=rsa-sha256; c=relaxed/relaxed;
 d=example.com; s=selector; h=from:to:subject;
 bh=...; b=...
```

### Configuración DKIM

#### Generar Claves
```bash
# Usando opendkim
opendkim-genkey -s selector -d example.com

# Usando Python
python3 -c "
import dkim
key = dkim.rsa_key_gen()
print('Private key:')
print(key[0].decode())
print('Public key:')
print(key[1].decode())
"
```

#### En Postfix
```postfix
# main.cf
smtpd_milters = inet:localhost:8891
non_smtpd_milters = inet:localhost:8891
milter_default_action = accept
```

#### Verificación DKIM
```bash
# Verificar clave pública
dig TXT selector._domainkey.example.com

# Probar DKIM
dkimpy-milter --test
```

## DMARC (Domain-based Message Authentication, Reporting and Conformance)

### ¿Qué es DMARC?

DMARC combina SPF y DKIM, proporcionando políticas para manejar emails que fallan la autenticación y reportes sobre la actividad del dominio.

### Cómo Funciona DMARC

1. **Publicación:** Política DMARC en `_dmarc.example.com`
2. **Evaluación:** Verifica SPF y/o DKIM
3. **Acción:** Aplica política según resultado
4. **Reportes:** Envía reportes XML al dominio

### Registro DMARC

```
v=DMARC1; p=quarantine; rua=mailto:dmarc@example.com; ruf=mailto:dmarc@example.com; fo=1
```

#### Parámetros Principales

| Parámetro | Descripción | Valores |
|-----------|-------------|---------|
| `p` | Política | `none`, `quarantine`, `reject` |
| `sp` | Política subdominios | `none`, `quarantine`, `reject` |
| `rua` | Reportes agregados | `mailto:usuario@dominio.com` |
| `ruf` | Reportes forenses | `mailto:usuario@dominio.com` |
| `fo` | Opciones de reporte | `0`, `1`, `d`, `s` |
| `adkim` | Alineación DKIM | `r` (relaxed), `s` (strict) |
| `aspf` | Alineación SPF | `r` (relaxed), `s` (strict) |

### Políticas DMARC

#### p=none
- **Acción:** No hacer nada
- **Uso:** Modo monitor, solo reportes
- **Ejemplo:** `p=none; rua=mailto:dmarc@example.com`

#### p=quarantine
- **Acción:** Enviar a spam
- **Uso:** Protección moderada
- **Ejemplo:** `p=quarantine; rua=mailto:dmarc@example.com`

#### p=reject
- **Acción:** Rechazar email
- **Uso:** Máxima protección
- **Ejemplo:** `p=reject; rua=mailto:dmarc@example.com`

### Configuración DMARC

#### Registro DNS
```bind
_dmarc IN TXT "v=DMARC1; p=quarantine; rua=mailto:dmarc@example.com; ruf=mailto:dmarc@example.com; fo=1; adkim=r; aspf=r"
```

#### Verificación
```bash
# Verificar registro DMARC
dig TXT _dmarc.example.com

# Validar sintaxis
dmarc-validate example.com
```

## Implementación Completa

### Secuencia de Configuración

1. **Configurar SPF**
2. **Implementar DKIM**
3. **Publicar DMARC en modo monitor (p=none)**
4. **Analizar reportes**
5. **Ajustar políticas gradualmente**

### Ejemplo Completo

#### 1. SPF Record
```
v=spf1 include:_spf.google.com include:spf.protection.outlook.com -all
```

#### 2. DKIM Keys
```bash
# Generar para Google Workspace
# Las claves se generan automáticamente en admin.google.com
```

#### 3. DMARC Record
```
v=DMARC1; p=quarantine; rua=mailto:dmarc@example.com; ruf=mailto:dmarc@example.com; fo=1; pct=100
```

### Herramientas de Testing

#### Validadores Online
- **MX Toolbox:** SPF, DKIM, DMARC checker
- **Mail Tester:** Envía email de prueba
- **DMARC Analyzer:** Analiza reportes

#### Comandos
```bash
# Verificar todos los registros
dig TXT example.com _dmarc.example.com selector._domainkey.example.com

# Enviar email de prueba
swaks --to test@example.com --from user@example.com --server mail.example.com --tls
```

## Reportes DMARC

### Tipos de Reportes

#### Reportes Agregados (RUA)
- **Formato:** XML comprimido
- **Frecuencia:** Diaria
- **Contenido:** Estadísticas de autenticación

#### Reportes Forenses (RUF)
- **Formato:** Email con detalles
- **Frecuencia:** Por email fallido
- **Contenido:** Headers completos

### Análisis de Reportes

```xml
<?xml version="1.0" encoding="UTF-8"?>
<feedback>
  <report_metadata>
    <org_name>google.com</org_name>
    <email>noreply-dmarc-support@google.com</email>
    <report_id>123456789</report_id>
  </report_metadata>
  <policy_published>
    <domain>example.com</domain>
    <adkim>r</adkim>
    <aspf>r</aspf>
    <p>quarantine</p>
  </policy_published>
  <record>
    <row>
      <source_ip>192.168.1.1</source_ip>
      <count>100</count>
      <policy_evaluated>
        <disposition>quarantine</disposition>
        <dkim>pass</dkim>
        <spf>fail</spf>
      </policy_evaluated>
    </row>
  </record>
</feedback>
```

### Herramientas de Análisis

- **DMARC Report Analyzer:** Parser online
- **dmarcian:** Servicio comercial
- **Scripts personalizados:** Procesar XML con Python

```python
import xml.etree.ElementTree as ET
import gzip

def parse_dmarc_report(filename):
    with gzip.open(filename, 'rb') as f:
        tree = ET.parse(f)
    root = tree.getroot()
    
    for record in root.findall('.//record'):
        row = record.find('row')
        source_ip = row.find('source_ip').text
        count = int(row.find('count').text)
        disposition = row.find('.//disposition').text
        
        print(f"IP: {source_ip}, Count: {count}, Disposition: {disposition}")

# Uso
parse_dmarc_report('dmarc_report.xml.gz')
```

## Mejores Prácticas

### Configuración Inicial
1. **Empezar con p=none** para monitorizar
2. **Configurar reportes** para análisis
3. **Gradualmente aumentar** la política

### Mantenimiento
- **Monitorear reportes** regularmente
- **Actualizar registros** cuando cambian IPs
- **Usar subdominios** específicos para email

### Consideraciones de Seguridad
- **Rotar claves DKIM** periódicamente
- **Proteger claves privadas** de accesos no autorizados
- **Usar DNSSEC** para proteger registros

## Referencias

- RFC 7208: Sender Policy Framework (SPF)
- RFC 6376: DomainKeys Identified Mail (DKIM)
- RFC 7489: Domain-based Message Authentication, Reporting, and Conformance (DMARC)
- RFC 8461: SMTP MTA Strict Transport Security (MTA-STS)
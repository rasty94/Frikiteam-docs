---
title: DNSSEC
description: Introducción a la firma criptográfica de zonas DNS para evitar envenenamiento de caché.
draft: false
updated: 2026-01-25
---

# DNSSEC (Domain Name System Security Extensions)

DNSSEC extiende el protocolo DNS para proporcionar autenticación de origen de datos, integridad de datos y autenticación de existencia (o no existencia) de datos, previniendo ataques como el envenenamiento de caché DNS.

## Conceptos Básicos

### ¿Por qué DNSSEC?

El DNS tradicional no proporciona:

- **Autenticación:** Verificar que la respuesta viene del servidor autorizado
- **Integridad:** Garantizar que los datos no han sido modificados
- **Negación de existencia:** Probar que un nombre no existe

DNSSEC resuelve estos problemas mediante criptografía de clave pública.

### Componentes Principales

#### ZSK (Zone Signing Key)
- **Propósito:** Firmar registros de zona
- **Tamaño:** 1024-4096 bits
- **Rotación:** Periódica (3-12 meses)

#### KSK (Key Signing Key)
- **Propósito:** Firmar ZSK y DS records
- **Tamaño:** Mayor que ZSK (2048-4096 bits)
- **Rotación:** Menos frecuente (1-5 años)

#### DS (Delegation Signer) Record
- **Propósito:** Conecta zona padre con hija
- **Contenido:** Hash de la KSK pública
- **Publicación:** En zona padre

## Cómo Funciona DNSSEC

### Proceso de Validación

1. **Consulta DNS:** Cliente solicita `www.example.com`
2. **Respuesta firmada:** Servidor devuelve registros + firma RRSIG
3. **Validación de cadena:**
   - Verificar firma con clave pública (DNSKEY)
   - Validar DS record en zona padre
   - Confirmar confianza hasta root
4. **Resultado:** Datos autenticados o error

### Tipos de Registros DNSSEC

| Registro | Propósito | Descripción |
|----------|-----------|-------------|
| DNSKEY | Claves públicas | Contiene ZSK y KSK públicas |
| RRSIG | Firmas | Firma de registros RRSET |
| NSEC | Prueba de no existencia | Lista siguiente nombre existente |
| NSEC3 | Prueba de no existencia | Versión hasheada de NSEC |
| DS | Delegation Signer | Conecta zonas padre-hija |
| CDS/CDNSKEY | Cambio de claves | Automatiza actualización DS |

## Configuración DNSSEC

### En BIND9

#### 1. Generar Claves
```bash
# Crear directorio KSK/ZSK
mkdir -p /etc/bind/keys/example.com

# Generar KSK (Key Signing Key)
dnssec-keygen -a RSASHA256 -b 2048 -n ZONE -f KSK example.com

# Generar ZSK (Zone Signing Key)
dnssec-keygen -a RSASHA256 -b 1024 -n ZONE example.com
```

#### 2. Firmar Zona
```bash
# Firmar zona con claves generadas
dnssec-signzone -o example.com -k Kexample.com.+008+12345 example.com Kexample.com.+008+67890

# Verificar firma
dnssec-verify example.com.signed
```

#### 3. Configurar named.conf
```bind
zone "example.com" {
    type master;
    file "/etc/bind/zones/example.com.signed";
    key-directory "/etc/bind/keys/example.com";
};
```

#### 4. Publicar DS Record
```bash
# Extraer DS record
dnssec-dsfromkey Kexample.com.+008+12345

# Publicar en registrador
# ds1.example.com. IN DS 12345 8 2 1234567890ABCDEF...
```

### Automatización con Scripts

```bash
#!/bin/bash
# Script para firmar zona automáticamente

ZONE="example.com"
ZONEDIR="/etc/bind/zones"
KEYDIR="/etc/bind/keys/$ZONE"

# Firmar zona
dnssec-signzone -o $ZONE -d $ZONEDIR -k $KEYDIR/K${ZONE}.+008+$(cat $KEYDIR/K${ZONE}.+008+*.key | grep -o 'key [0-9]*' | cut -d' ' -f2) $ZONEDIR/$ZONE

# Recargar zona
rndc reload $ZONE
```

## Validación del Lado Cliente

### Configuración del Resolver

#### En /etc/resolv.conf
```
nameserver 8.8.8.8  # Google DNS (soporta DNSSEC)
nameserver 1.1.1.1  # Cloudflare DNS (soporta DNSSEC)
```

#### En BIND Local
```bind
options {
    dnssec-enable yes;
    dnssec-validation yes;
    dnssec-lookaside auto;
};
```

#### En Unbound
```unbound
server:
    do-dnssec: yes
    trust-anchor-file: "/etc/unbound/root.key"
```

### Verificación de Validación

```bash
# Verificar soporte DNSSEC
dig @8.8.8.8 www.dnssec-failed.org +dnssec

# Ver registros DNSSEC
dig example.com DNSKEY +dnssec

# Ver firma
dig example.com A +dnssec
```

## NSEC vs NSEC3

### NSEC (Next Secure)

- **Funcionamiento:** Lista el siguiente nombre existente
- **Ventaja:** Simple y eficiente
- **Desventaja:** Permite enumeración de zona

```
www.example.com. NSEC mail.example.com. A RRSIG NSEC
```

### NSEC3

- **Funcionamiento:** Usa hash del nombre de dominio
- **Ventaja:** Previene enumeración de zona
- **Desventaja:** Más complejo y overhead

```
7P5G3N8A1E8B4C2D6F9H0J5K.example.com. NSEC3 1 0 10 1234567890ABCDEF L8R4M6N2P0Q5S7T9V1W3X5Y7Z
```

### Configuración NSEC3
```bash
# Firmar con NSEC3
dnssec-signzone -o example.com -3 $(head -c 1000 /dev/random | sha1sum | cut -b 1-16) -H 10 example.com
```

## Rotación de Claves

### Proceso de Rotación ZSK

1. **Generar nueva ZSK**
2. **Añadir a zona y firmar**
3. **Esperar propagación (TTL)**
4. **Remover antigua ZSK**

### Proceso de Rotación KSK

1. **Generar nueva KSK**
2. **Crear nuevo DS record**
3. **Publicar DS en zona padre**
4. **Esperar propagación DS (2 días)**
5. **Remover antigua KSK**

### Automatización
```bash
# Usando dnssec-tools
dnssec-tools rollover example.com ZSK
dnssec-tools rollover example.com KSK
```

## Monitoreo y Troubleshooting

### Herramientas de Diagnóstico

#### Verificación Básica
```bash
# Verificar firma de zona
dnssec-verify example.com.signed

# Probar resolución DNSSEC
dig @127.0.0.1 example.com A +dnssec

# Ver estado de validación
drill -D example.com
```

#### Scripts de Monitoreo
```bash
#!/bin/bash
# Verificar DNSSEC para dominio

DOMAIN="example.com"
DNSSEC_OK=0

# Verificar DNSKEY
if dig $DOMAIN DNSKEY +short | grep -q "DNSKEY"; then
    echo "✓ DNSKEY presente"
    DNSSEC_OK=$((DNSSEC_OK+1))
else
    echo "✗ Falta DNSKEY"
fi

# Verificar RRSIG
if dig $DOMAIN A +dnssec | grep -q "RRSIG"; then
    echo "✓ RRSIG presente"
    DNSSEC_OK=$((DNSSEC_OK+1))
else
    echo "✗ Falta RRSIG"
fi

# Verificar DS
if dig $DOMAIN DS +short | grep -q "DS"; then
    echo "✓ DS presente"
    DNSSEC_OK=$((DNSSEC_OK+1))
else
    echo "✗ Falta DS"
fi

if [ $DNSSEC_OK -eq 3 ]; then
    echo "✓ DNSSEC configurado correctamente"
else
    echo "✗ Problemas con DNSSEC"
fi
```

### Problemas Comunes

#### 1. SERVFAIL
- **Causa:** Error de validación
- **Solución:** Verificar claves y firmas

#### 2. Falta DS Record
- **Causa:** No publicado en zona padre
- **Solución:** Contactar registrador

#### 3. Claves Expiradas
- **Causa:** RRSIG expirado
- **Solución:** Refirmar zona

#### 4. Inconsistencia de Serial
- **Causa:** Serial no incrementado
- **Solución:** Actualizar serial antes de firmar

## DNSSEC en la Práctica

### Casos de Uso

#### Dominios Públicos
- **Ventaja:** Protección contra cache poisoning
- **Complejidad:** Requiere coordinación con registrador

#### Redes Corporativas
- **Uso:** DNSSEC interno para Active Directory
- **Implementación:** Políticas de grupo

#### Servicios Cloud
- **AWS Route 53:** Soporte nativo DNSSEC
- **Cloudflare:** DNSSEC automático

### Mejores Prácticas

1. **Empezar pequeño:** Probar con subdominio
2. **Automatizar:** Scripts para rotación de claves
3. **Monitorear:** Alertas de fallos de validación
4. **Documentar:** Procedimientos de recuperación

### Consideraciones de Rendimiento

- **Overhead:** Aumento de tamaño de respuestas (~20-30%)
- **Latencia:** Consultas adicionales para validación
- **CPU:** Costo criptográfico en servidores

## Referencias

- RFC 4033: DNS Security Introduction and Requirements
- RFC 4034: Resource Records for the DNS Security Extensions
- RFC 4035: Protocol Modifications for the DNS Security Extensions
- RFC 5155: DNS Security (DNSSEC) Hashed Authenticated Denial of Existence
- RFC 6781: DNSSEC Operational Practices, Version 2
# 🚧 TRANSLATION PENDING

> Pending translation. Original:

---

---
title: Registros PTR y Zonas Inversas
description: Cómo funcionan las búsquedas inversas (in-addr.arpa) y su importancia para la reputación de IP.
draft: false
---

# Registros PTR y Zonas Inversas

Los registros PTR (Pointer) permiten la resolución inversa de direcciones IP a nombres de dominio. Son cruciales para la reputación de email, seguridad y diagnóstico de red.

## Conceptos Básicos

### ¿Qué es una Búsqueda Inversa?

La resolución inversa traduce una dirección IP en un nombre de dominio:

- **Forward DNS:** `www.example.com` → `192.168.1.1`
- **Reverse DNS:** `192.168.1.1` → `www.example.com`

### Registros PTR

- **Tipo:** PTR
- **Propósito:** Apuntar a un nombre de dominio
- **Sintaxis:** `dirección_IP.in-addr.arpa. IN PTR nombre_dominio.`

## Estructura de Zonas Inversas

### Zona in-addr.arpa

Para IPv4, las zonas inversas están bajo `in-addr.arpa`:

- **Estructura:** Reversa de la IP + `.in-addr.arpa`
- **Ejemplo:** `192.168.1.1` → `1.1.168.192.in-addr.arpa`

### Delegación de Zonas

Las zonas inversas se delegan por octetos:

- **/8:** Delegado a RIRs (ARIN, RIPE, etc.)
- **/16:** ISP o organización grande
- **/24:** Subred típica

### Archivo de Zona Inversa

```bind
$TTL 86400
@ IN SOA ns1.example.com. admin.example.com. (
    2023120101 ; Serial
    3600       ; Refresh
    1800       ; Retry
    604800     ; Expire
    86400      ; Minimum TTL
)

@ IN NS ns1.example.com.
@ IN NS ns2.example.com.

; Registros PTR
1 IN PTR host1.example.com.
2 IN PTR host2.example.com.
10 IN PTR mail.example.com.
```

## Configuración en Diferentes Servidores

### BIND9

#### Archivo de zona
```
zone "1.168.192.in-addr.arpa" {
    type master;
    file "/etc/bind/zones/db.192.168.1";
};
```

#### Contenido de zona inversa
```bind
$ORIGIN 1.168.192.in-addr.arpa.
$TTL 86400
@ IN SOA ns1.example.com. admin.example.com. (
    2023120101  ; Serial
    3H          ; Refresh
    1H          ; Retry
    1W          ; Expire
    1D          ; Minimum
)

    IN NS ns1.example.com.
    IN NS ns2.example.com.

1   IN PTR www.example.com.
2   IN PTR mail.example.com.
100 IN PTR dhcp-100.example.com.
```

### Windows DNS Server

1. **Crear zona inversa:** DNS Manager → New Zone → Reverse Lookup Zone
2. **Tipo:** Primary zone
3. **Red:** 192.168.1.0/24
4. **Añadir registros PTR:** Right-click → New Pointer (PTR)

### PowerDNS

```sql
-- Insertar zona inversa
INSERT INTO domains (name, type) VALUES ('1.168.192.in-addr.arpa', 'MASTER');

-- Insertar registros PTR
INSERT INTO records (domain_id, name, type, content, ttl)
VALUES (
    (SELECT id FROM domains WHERE name='1.168.192.in-addr.arpa'),
    '1.1.168.192.in-addr.arpa',
    'PTR',
    'www.example.com',
    86400
);
```

## IPv6 Reverse DNS

### Zona ip6.arpa

Para IPv6, se usa `ip6.arpa` en lugar de `in-addr.arpa`.

#### Estructura
- Dirección IPv6: `2001:db8:85a3::8a2e:370:7334`
- Reverse: `4.3.3.7.0.7.3.e.2.a.8.0.0.0.0.0.0.3.a.5.8.8.b.d.0.1.0.0.2.ip6.arpa`

#### Simplificación
Se puede abreviar invirtiendo nibbles (4 bits):

```
2001:db8:85a3::8a2e:370:7334
↓
4.3.3.7.0.7.3.e.2.a.8.0.0.0.0.0.0.3.a.5.8.8.b.d.0.1.0.0.2.ip6.arpa
```

### Configuración IPv6 Reverse

```bind
$ORIGIN 3.a.5.8.8.b.d.0.1.0.0.2.ip6.arpa.
$TTL 86400
@ IN SOA ns1.example.com. admin.example.com. (
    2023120101
    3H
    1H
    1W
    1D
)

    IN NS ns1.example.com.

4.3.3.7.0.7.3.e.2.a.8 IN PTR www.example.com.
```

## Importancia para la Reputación

### Email Delivery

Los servidores de email verifican PTR para combatir spam:

```bash
# Verificar PTR
dig -x 192.168.1.1

# Verificar SPF
dig TXT example.com

# Verificar DKIM
dig TXT dkim._domainkey.example.com
```

### Filtros Antispam

- **Hotmail/Outlook:** Requiere PTR válido
- **Gmail:** Usa PTR como factor de reputación
- **Spamhaus:** Lista IPs sin PTR válido

### Mejores Prácticas

1. **PTR debe resolver:** `host IP` debe devolver nombre válido
2. **Consistencia:** PTR debe coincidir con A/AAAA records
3. **Unicidad:** Una IP debe tener solo un PTR
4. **Dominio propio:** Usar subdominio propio (mail.example.com)

## Diagnóstico y Troubleshooting

### Herramientas de Verificación

#### Comando host
```bash
host 192.168.1.1
# Debe devolver: 192.168.1.1.in-addr.arpa domain name pointer mail.example.com
```

#### Dig
```bash
# Consulta PTR
dig PTR 1.1.168.192.in-addr.arpa

# Consulta inversa simplificada
dig -x 192.168.1.1
```

#### Nslookup
```bash
nslookup
> set type=PTR
> 1.1.168.192.in-addr.arpa
```

### Problemas Comunes

#### 1. PTR no configurado
```
;; ANSWER SECTION:
;; No answer
```

#### 2. Delegación incorrecta
```
;; AUTHORITY SECTION:
1.168.192.in-addr.arpa. 86400 IN NS ns1.isp.com.
```

#### 3. TTL inconsistente
PTR con TTL diferente al A record puede causar problemas de caché.

### Scripts de Monitoreo

```bash
#!/bin/bash
# Verificar PTR para rango de IPs

for i in {1..254}; do
    ip="192.168.1.$i"
    ptr=$(dig -x $ip +short)
    if [ -z "$ptr" ]; then
        echo "WARNING: No PTR for $ip"
    else
        echo "OK: $ip -> $ptr"
    fi
done
```

## Casos de Uso Avanzados

### Load Balancing

PTR para IPs de balanceadores:

```
10 IN PTR lb1.example.com.
10 IN PTR lb2.example.com.  ; No recomendado - solo un PTR por IP
```

### CDN y Hosting Compartido

- **Problema:** Múltiples dominios en misma IP
- **Solución:** PTR genérico o subdominios

### VPN y Remote Access

PTR para IPs asignadas dinámicamente:

```
100 IN PTR vpn-user-001.example.com.
101 IN PTR vpn-user-002.example.com.
```

## Seguridad

### Consideraciones

- **Información leakage:** PTR puede revelar estructura interna
- **Spoofing:** Ataques de DNS spoofing afectan PTR
- **Cache poisoning:** Ataques a servidores DNS

### Mejores Prácticas de Seguridad

1. **DNSSEC:** Firmar zonas inversas
2. **Split DNS:** Zonas internas vs externas diferentes
3. **Rate limiting:** Limitar consultas inversas
4. **Monitoreo:** Alertas de cambios en PTR

## Referencias

- RFC 1035: Domain Names - Implementation and Specification
- RFC 2317: Classless IN-ADDR.ARPA delegation
- RFC 3596: DNS Extensions to Support IP Version 6
- RFC 5855: Nameservers for IPv4 and IPv6 Reverse Zones
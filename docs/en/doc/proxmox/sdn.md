# 🚧 TRANSLATION PENDING

> Pending translation. Original:

---

# Infraestructura: Proxmox SDN

Configuración avanzada de redes definidas por software en Proxmox VE.

## Resumen

Implementación de VXLAN y EVPN para segmentación de red multi-tenant.

## Prerrequisitos

- Proxmox VE 8.1 o superior.
- Paquete `libpve-network-perl` instalado.
- Soporte para MTU jumbo (9000) en el switch físico (recomendado).

## Configuración de Zona VXLAN

1. Nodo > SDN > Zones > Add > VXLAN.
2. ID: `vnnet`.
3. Peers: IPs de los nodos del cluster.

## Referencias

- [Proxmox SDN Documentation](https://pve.proxmox.com/wiki/Software_Defined_Network)

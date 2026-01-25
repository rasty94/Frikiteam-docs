#!/usr/bin/env python3
"""
Analizador de logs de acceso para documentación estática.
Genera estadísticas básicas sin tracking invasivo.

Uso:
    python scripts/analyze_logs.py /var/log/nginx/access.log
    python scripts/analyze_logs.py --days 30 /var/log/nginx/access.log
    python scripts/analyze_logs.py --top 20 /var/log/nginx/access.log
"""

import re
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple
import urllib.parse


# Patrón para logs de Nginx/Apache (formato combined)
LOG_PATTERN = re.compile(
    r'(?P<ip>[\d\.]+) - - \[(?P<date>[^\]]+)\] '
    r'"(?P<method>\w+) (?P<path>[^\s]+) HTTP/[\d\.]+" '
    r'(?P<status>\d+) (?P<size>\d+|-) '
    r'"(?P<referrer>[^"]*)" "(?P<user_agent>[^"]*)"'
)


class LogAnalyzer:
    """Analiza logs de acceso web y genera estadísticas."""
    
    def __init__(self, logfile: Path, days: int = 30):
        self.logfile = logfile
        self.days = days
        self.cutoff_date = datetime.now() - timedelta(days=days)
        
        # Contadores
        self.page_views = Counter()
        self.status_codes = Counter()
        self.referrers = Counter()
        self.daily_visits = defaultdict(int)
        self.user_agents = Counter()
        
        # Stats
        self.total_requests = 0
        self.unique_ips = set()
        self.bots = Counter()
        
    def is_bot(self, user_agent: str) -> bool:
        """Detecta si el user agent es un bot."""
        bot_patterns = [
            'bot', 'crawler', 'spider', 'scraper', 'curl', 'wget',
            'python-requests', 'go-http-client', 'java/', 'okhttp'
        ]
        ua_lower = user_agent.lower()
        return any(pattern in ua_lower for pattern in bot_patterns)
    
    def clean_path(self, path: str) -> str:
        """Limpia y normaliza el path."""
        # Decodifica URL
        path = urllib.parse.unquote(path)
        
        # Ignora query params
        if '?' in path:
            path = path.split('?')[0]
        
        # Normaliza trailing slash
        if path.endswith('/') and path != '/':
            path = path[:-1]
        
        return path
    
    def parse_date(self, date_str: str) -> datetime:
        """Parsea fecha del log (formato: 25/Jan/2026:14:30:45 +0000)."""
        try:
            # Formato: 25/Jan/2026:14:30:45 +0000
            dt = datetime.strptime(date_str.split()[0], '%d/%b/%Y:%H:%M:%S')
            return dt
        except ValueError:
            return datetime.now()
    
    def should_count(self, path: str, status: str, user_agent: str) -> bool:
        """Determina si una request debe contarse."""
        # Ignorar assets estáticos
        static_extensions = [
            '.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.svg',
            '.ico', '.woff', '.woff2', '.ttf', '.eot', '.map'
        ]
        if any(path.endswith(ext) for ext in static_extensions):
            return False
        
        # Solo contar éxitos (200-299)
        if not status.startswith('2'):
            return False
        
        # Ignorar bots (opcional, pero sesgará stats)
        # if self.is_bot(user_agent):
        #     return False
        
        return True
    
    def parse_log(self):
        """Parsea el archivo de log."""
        print(f"📂 Analizando logs de los últimos {self.days} días...")
        print(f"📅 Desde: {self.cutoff_date.strftime('%Y-%m-%d')}\n")
        
        if not self.logfile.exists():
            print(f"❌ Error: No se encuentra {self.logfile}")
            return
        
        with open(self.logfile, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                match = LOG_PATTERN.match(line)
                if not match:
                    continue
                
                data = match.groupdict()
                
                # Parsear fecha
                log_date = self.parse_date(data['date'])
                if log_date < self.cutoff_date:
                    continue
                
                self.total_requests += 1
                self.unique_ips.add(data['ip'])
                
                # User agent
                user_agent = data['user_agent']
                if self.is_bot(user_agent):
                    self.bots[user_agent] += 1
                
                # Status codes
                self.status_codes[data['status']] += 1
                
                # Solo contar páginas válidas
                path = self.clean_path(data['path'])
                if not self.should_count(path, data['status'], user_agent):
                    continue
                
                # Estadísticas
                self.page_views[path] += 1
                self.daily_visits[log_date.strftime('%Y-%m-%d')] += 1
                
                # Referrers (sin detalles de tracking)
                referrer = data['referrer']
                if referrer and referrer != '-':
                    # Extraer solo el dominio
                    try:
                        parsed = urllib.parse.urlparse(referrer)
                        domain = parsed.netloc or 'Direct'
                    except:
                        domain = 'Unknown'
                    self.referrers[domain] += 1
    
    def print_stats(self, top_n: int = 10):
        """Imprime estadísticas."""
        print("=" * 70)
        print(f"📊 ESTADÍSTICAS DE ACCESO - Últimos {self.days} días")
        print("=" * 70)
        print(f"\n📈 Resumen General:")
        print(f"   Total de requests: {self.total_requests:,}")
        print(f"   IPs únicas: {len(self.unique_ips):,}")
        print(f"   Páginas vistas: {sum(self.page_views.values()):,}")
        print(f"   Bots detectados: {sum(self.bots.values()):,} ({len(self.bots)} tipos)")
        
        # Top páginas
        print(f"\n📄 Top {top_n} Páginas Más Visitadas:")
        print("-" * 70)
        for i, (page, count) in enumerate(self.page_views.most_common(top_n), 1):
            percentage = (count / sum(self.page_views.values())) * 100
            print(f"   {i:2}. {page:50} {count:>6} ({percentage:>5.1f}%)")
        
        # Status codes
        print(f"\n🔢 Códigos HTTP:")
        print("-" * 70)
        for status, count in sorted(self.status_codes.items()):
            percentage = (count / self.total_requests) * 100
            emoji = "✅" if status.startswith('2') else "⚠️" if status.startswith('3') else "❌"
            print(f"   {emoji} {status}: {count:>6} ({percentage:>5.1f}%)")
        
        # Referrers
        if self.referrers:
            print(f"\n🔗 Top {min(top_n, len(self.referrers))} Fuentes de Tráfico:")
            print("-" * 70)
            for i, (referrer, count) in enumerate(self.referrers.most_common(top_n), 1):
                percentage = (count / sum(self.referrers.values())) * 100
                print(f"   {i:2}. {referrer:50} {count:>6} ({percentage:>5.1f}%)")
        
        # Tendencia diaria
        if self.daily_visits:
            print(f"\n📅 Visitas Diarias (últimos 7 días):")
            print("-" * 70)
            sorted_days = sorted(self.daily_visits.items(), reverse=True)[:7]
            max_visits = max(v for _, v in sorted_days)
            
            for date, count in sorted_days:
                bar_length = int((count / max_visits) * 40)
                bar = "█" * bar_length
                print(f"   {date}: {bar} {count:>5}")
        
        # Top bots
        if self.bots:
            print(f"\n🤖 Top {min(5, len(self.bots))} Bots:")
            print("-" * 70)
            for i, (bot, count) in enumerate(self.bots.most_common(5), 1):
                # Truncar user agent largo
                bot_short = (bot[:60] + '...') if len(bot) > 60 else bot
                print(f"   {i}. {bot_short:63} {count:>6}")
        
        print("\n" + "=" * 70)
        print("✅ Análisis completado")
        print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description='Analiza logs de acceso y genera estadísticas'
    )
    parser.add_argument(
        'logfile',
        type=Path,
        help='Archivo de log a analizar (formato Nginx/Apache combined)'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=30,
        help='Número de días a analizar (default: 30)'
    )
    parser.add_argument(
        '--top',
        type=int,
        default=10,
        help='Número de resultados top a mostrar (default: 10)'
    )
    
    args = parser.parse_args()
    
    analyzer = LogAnalyzer(args.logfile, args.days)
    analyzer.parse_log()
    analyzer.print_stats(args.top)


if __name__ == '__main__':
    main()

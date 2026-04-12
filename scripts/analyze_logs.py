#!/usr/bin/env python3
"""
ScamGuard AI - Bot Log Analyzer
Автоматическая обработка логов бота с красивым оформлением
Создаёт понятные отчёты для обычной аудитории
"""

import re
import sys
from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict

# Colors for terminal output
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    END = '\033[0m'
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_BLUE = '\033[44m'


def parse_log_line(line):
    """Parse a single log line"""
    # Pattern: HH:MM:SS | LEVEL | message
    pattern = r'(\d{2}:\d{2}:\d{2})\s*\|\s*(INFO|WARNING|ERROR|DEBUG)\s*\|\s*(.*)'
    match = re.match(pattern, line.strip())
    
    if match:
        return {
            'time': match.group(1),
            'level': match.group(2),
            'message': match.group(3).strip()
        }
    return None


def analyze_logs(log_file_path):
    """Analyze log file and return structured data"""
    logs = []
    
    with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            parsed = parse_log_line(line)
            if parsed:
                logs.append(parsed)
    
    return logs


def get_log_statistics(logs):
    """Calculate statistics from logs"""
    stats = {
        'total_entries': len(logs),
        'levels': Counter(),
        'errors': [],
        'warnings': [],
        'bot_events': [],
        'api_calls': [],
        'user_actions': [],
        'time_range': {'start': None, 'end': None},
        'startup_info': {},
        'conflict_errors': 0,
        'success_count': 0,
    }
    
    for log in logs:
        stats['levels'][log['level']] += 1
        
        msg = log['message']
        
        # Track time range
        if not stats['time_range']['start']:
            stats['time_range']['start'] = log['time']
        stats['time_range']['end'] = log['time']
        
        # Categorize messages
        if log['level'] == 'ERROR':
            stats['errors'].append(log)
            if 'Conflict' in msg or 'conflict' in msg.lower():
                stats['conflict_errors'] += 1
        
        elif log['level'] == 'WARNING':
            stats['warnings'].append(log)
        
        # Bot startup info
        if 'Bot Starting' in msg:
            stats['startup_info']['start_time'] = log['time']
        if 'Bot username' in msg:
            username_match = re.search(r'@(\w+)', msg)
            if username_match:
                stats['startup_info']['username'] = username_match.group(1)
        if 'Bot is ready' in msg:
            stats['startup_info']['ready_time'] = log['time']
            stats['success_count'] += 1
        
        # User actions
        if any(kw in msg.lower() for kw in ['user', 'message', 'analyze', 'quick check', 'deep analysis']):
            stats['user_actions'].append(log)
        
        # API calls
        if 'API' in msg or 'endpoint' in msg.lower():
            stats['api_calls'].append(log)
    
    return stats


def create_ascii_bar(value, max_value, width=30, char='█'):
    """Create ASCII bar chart"""
    if max_value == 0:
        return '░' * width
    filled = int((value / max_value) * width)
    return char * filled + '░' * (width - filled)


def print_beautiful_report(stats, log_file_path):
    """Print beautiful human-readable report"""
    
    # Header
    print()
    print(f"{Colors.CYAN}{'═' * 70}{Colors.END}")
    print(f"{Colors.CYAN}{'🛡️  SCAMGUARD AI - ОТЧЁТ РАБОТЫ БОТА':^70}{Colors.END}")
    print(f"{Colors.CYAN}{'═' * 70}{Colors.END}")
    print()
    
    # File info
    log_path = Path(log_file_path)
    file_size = log_path.stat().st_size
    
    print(f"{Colors.DIM}📁 Файл логов:{Colors.END} {log_path.name}")
    print(f"{Colors.DIM}📏 Размер файла:{Colors.END} {file_size / 1024:.1f} KB")
    print(f"{Colors.DIM}📊 Записей в логе:{Colors.END} {stats['total_entries']}")
    print(f"{Colors.DIM}⏰ Период:{Colors.END} {stats['time_range']['start']} - {stats['time_range']['end']}")
    print()
    
    # Bot Status Section
    print(f"{Colors.GREEN}{'─' * 70}{Colors.END}")
    print(f"{Colors.GREEN}{'🤖 СТАТУС БОТА':^70}{Colors.END}")
    print(f"{Colors.GREEN}{'─' * 70}{Colors.END}")
    print()
    
    if stats['startup_info']:
        startup = stats['startup_info']
        
        status_icon = '✅' if startup.get('ready_time') else '❌'
        status_text = 'РАБОТАЕТ' if startup.get('ready_time') else 'НЕ ЗАПУЩЕН'
        status_color = Colors.GREEN if startup.get('ready_time') else Colors.RED
        
        print(f"{status_color}  Статус: {status_icon} {status_text}{Colors.END}")
        print(f"  Username: @{startup.get('username', 'Неизвестно')}")
        print(f"  Запущен в: {startup.get('start_time', 'Неизвестно')}")
        
        if startup.get('ready_time'):
            print(f"  Готов к работе: {startup.get('ready_time', 'Неизвестно')}")
    else:
        print(f"  {Colors.RED}❌ Информация о запуске не найдена{Colors.END}")
    
    print()
    
    # Log Levels Distribution
    print(f"{Colors.BLUE}{'─' * 70}{Colors.END}")
    print(f"{Colors.BLUE}{'📊 РАСПРЕДЕЛЕНИЕ СОБЫТИЙ ПО УРОВНЯМ':^70}{Colors.END}")
    print(f"{Colors.BLUE}{'─' * 70}{Colors.END}")
    print()
    
    level_icons = {
        'INFO': 'ℹ️',
        'WARNING': '⚠️',
        'ERROR': '❌',
        'DEBUG': '🔍'
    }
    
    level_colors = {
        'INFO': Colors.GREEN,
        'WARNING': Colors.YELLOW,
        'ERROR': Colors.RED,
        'DEBUG': Colors.DIM
    }
    
    total = stats['total_entries']
    
    for level in ['INFO', 'WARNING', 'ERROR', 'DEBUG']:
        count = stats['levels'].get(level, 0)
        percentage = (count / total * 100) if total > 0 else 0
        icon = level_icons[level]
        color = level_colors[level]
        
        bar = create_ascii_bar(count, total, 40)
        
        print(f"  {icon} {color}{level:<10}{Colors.END} {count:>5} ({percentage:>5.1f}%)  {color}{bar}{Colors.END}")
    
    print()
    
    # Errors Section
    if stats['errors']:
        print(f"{Colors.RED}{'─' * 70}{Colors.END}")
        print(f"{Colors.RED}{'🚨 ОШИБКИ (ТРЕБУЮТ ВНИМАНИЯ)':^70}{Colors.END}")
        print(f"{Colors.RED}{'─' * 70}{Colors.END}")
        print()
        
        for i, error in enumerate(stats['errors'][:10], 1):
            # Simplify error message for humans
            msg = error['message']
            
            # Categorize error type
            if 'Conflict' in msg or 'conflict' in msg.lower():
                error_type = '⚔️ Конфликт процессов'
                suggestion = 'Запущено несколько копий бота! Убейте все процессы и запустите один.'
            elif 'Timeout' in msg or 'timeout' in msg.lower():
                error_type = '⏰ Превышение времени'
                suggestion = 'API или сеть работает медленно. Попробуйте позже.'
            elif 'Failed' in msg or 'failed' in msg.lower():
                error_type = '❌ Сбой операции'
                suggestion = 'Проверьте подключение к API и интернет.'
            else:
                error_type = '⚠️ Неизвестная ошибка'
                suggestion = 'Проверьте полный текст ошибки выше.'
            
            print(f"  {Colors.RED}{i}. {error_type}{Colors.END}")
            print(f"     {Colors.DIM}Время:{Colors.END} {error['time']}")
            print(f"     {Colors.DIM}Сообщение:{Colors.END} {msg[:80]}...")
            print(f"     {Colors.YELLOW}💡 Решение:{Colors.END} {suggestion}")
            print()
        
        if stats['conflict_errors'] > 0:
            print(f"  {Colors.RED}{'═' * 66}{Colors.END}")
            print(f"  {Colors.RED}⚔️  НАЙДЕНО КОНФЛИКТОВ БОТА: {stats['conflict_errors']}{Colors.END}")
            print(f"  {Colors.RED}{'═' * 66}{Colors.END}")
            print()
            print(f"  {Colors.YELLOW}🔧 Как исправить:{Colors.END}")
            print(f"     1. Остановите ВСЕ процессы: {Colors.CYAN}pkill -9 -f telegram_bot.py{Colors.END}")
            print(f"     2. Проверьте: {Colors.CYAN}ps aux | grep telegram_bot{Colors.END}")
            print(f"     3. Запустите ОДИН раз: {Colors.CYAN}python -m backend.bot.telegram_bot{Colors.END}")
            print()
    
    # Warnings Section
    if stats['warnings']:
        print(f"{Colors.YELLOW}{'─' * 70}{Colors.END}")
        print(f"{Colors.YELLOW}{'⚠️  ПРЕДУПРЕЖДЕНИЯ':^70}{Colors.END}")
        print(f"{Colors.YELLOW}{'─' * 70}{Colors.END}")
        print()
        
        for i, warning in enumerate(stats['warnings'][:5], 1):
            msg = warning['message']
            print(f"  {Colors.YELLOW}{i}. ⚠️{Colors.END} {msg[:90]}")
            print(f"     {Colors.DIM}Время: {warning['time']}{Colors.END}")
            print()
    
    # User Activity Section
    if stats['user_actions']:
        print(f"{Colors.MAGENTA}{'─' * 70}{Colors.END}")
        print(f"{Colors.MAGENTA}{'👤 АКТИВНОСТЬ ПОЛЬЗОВАТЕЛЕЙ':^70}{Colors.END}")
        print(f"{Colors.MAGENTA}{'─' * 70}{Colors.END}")
        print()
        
        print(f"  {Colors.DIM}Всего действий пользователей:{Colors.END} {len(stats['user_actions'])}")
        print()
        
        # Show last 5 user actions
        for action in stats['user_actions'][-5:]:
            msg = action['message']
            print(f"  {Colors.DIM}[{action['time']}]{Colors.END} {msg[:80]}")
        
        print()
    
    # Summary Section
    print(f"{Colors.CYAN}{'═' * 70}{Colors.END}")
    print(f"{Colors.CYAN}{'📋 ИТОГОВОЕ РЕЗЮМЕ':^70}{Colors.END}")
    print(f"{Colors.CYAN}{'═' * 70}{Colors.END}")
    print()
    
    # Calculate health score
    health_score = 100
    
    # Deduct for errors
    health_score -= len(stats['errors']) * 10
    
    # Deduct for warnings
    health_score -= len(stats['warnings']) * 5
    
    # Deduct for conflicts
    health_score -= stats['conflict_errors'] * 15
    
    health_score = max(0, min(100, health_score))
    
    # Health status
    if health_score >= 80:
        health_icon = '✅'
        health_text = 'ОТЛИЧНО'
        health_color = Colors.GREEN
    elif health_score >= 60:
        health_icon = '⚠️'
        health_text = 'НОРМАЛЬНО'
        health_color = Colors.YELLOW
    elif health_score >= 40:
        health_icon = '⚠️'
        health_text = 'ТРЕБУЕТ ВНИМАНИЯ'
        health_color = Colors.YELLOW
    else:
        health_icon = '❌'
        health_text = 'ПЛОХО'
        health_color = Colors.RED
    
    # Health bar
    health_bar = create_ascii_bar(health_score, 100, 50, '█')
    
    print(f"  {Colors.DIM}Здоровье системы:{Colors.END}")
    print(f"  {health_color}  {health_icon} {health_text} ({health_score}/100){Colors.END}")
    print(f"  {health_color}  {health_bar}{Colors.END}")
    print()
    
    # Stats grid
    print(f"  {Colors.DIM}📊 Статистика:{Colors.END}")
    print()
    print(f"    {Colors.GREEN}✅ Успешных:{Colors.END} {stats['success_count']}")
    print(f"    {Colors.RED}❌ Ошибок:{Colors.END} {len(stats['errors'])}")
    print(f"    {Colors.YELLOW}⚠️  Предупреждений:{Colors.END} {len(stats['warnings'])}")
    print(f"    {Colors.MAGENTA}👤 Действий пользователей:{Colors.END} {len(stats['user_actions'])}")
    print()
    
    # Recommendations
    if health_score < 100:
        print(f"  {Colors.YELLOW}{'─' * 66}{Colors.END}")
        print(f"  {Colors.YELLOW}💡 РЕКОМЕНДАЦИИ:{Colors.END}")
        print()
        
        if stats['conflict_errors'] > 0:
            print(f"  {Colors.RED}🔴{Colors.END} Устраните конфликты ботов (критично!)")
            print(f"     Команда: {Colors.CYAN}pkill -9 -f telegram_bot.py && python -m backend.bot.telegram_bot{Colors.END}")
            print()
        
        if len(stats['errors']) > 5:
            print(f"  {Colors.RED}🔴{Colors.END} Много ошибок - проверьте логи выше")
            print()
        
        if len(stats['warnings']) > 3:
            print(f"  {Colors.YELLOW}🟡{Colors.END} Обратите внимание на предупреждения")
            print()
        
        if health_score >= 80:
            print(f"  {Colors.GREEN}🟢{Colors.END} Система работает стабильно, мелких проблем нет")
            print()
    
    print(f"{Colors.CYAN}{'═' * 70}{Colors.END}")
    print()


def generate_html_report(stats, log_file_path, output_path):
    """Generate beautiful HTML report"""
    
    log_path = Path(log_file_path)
    
    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ScamGuard AI - Отчёт бота</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 40px 20px;
        }}
        
        .container {{
            max-width: 900px;
            margin: 0 auto;
        }}
        
        .header {{
            background: white;
            border-radius: 20px;
            padding: 40px;
            margin-bottom: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 2.5em;
            color: #667eea;
            margin-bottom: 10px;
        }}
        
        .header .subtitle {{
            color: #666;
            font-size: 1.1em;
        }}
        
        .card {{
            background: white;
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 20px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.08);
        }}
        
        .card h2 {{
            color: #333;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #667eea;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .card h2 .icon {{
            font-size: 1.5em;
        }}
        
        .status-badge {{
            display: inline-block;
            padding: 8px 20px;
            border-radius: 25px;
            font-weight: bold;
            font-size: 1.2em;
            margin: 10px 0;
        }}
        
        .status-success {{
            background: #4ade80;
            color: white;
        }}
        
        .status-warning {{
            background: #fbbf24;
            color: white;
        }}
        
        .status-error {{
            background: #f87171;
            color: white;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }}
        
        .stat-box {{
            background: #f8fafc;
            border-radius: 10px;
            padding: 20px;
            text-align: center;
        }}
        
        .stat-box .number {{
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
        }}
        
        .stat-box .label {{
            color: #666;
            margin-top: 5px;
        }}
        
        .error-item {{
            background: #fef2f2;
            border-left: 4px solid #f87171;
            padding: 15px;
            margin-bottom: 10px;
            border-radius: 5px;
        }}
        
        .error-item .time {{
            color: #999;
            font-size: 0.9em;
        }}
        
        .error-item .message {{
            color: #333;
            margin: 10px 0;
        }}
        
        .error-item .solution {{
            color: #16a34a;
            font-weight: bold;
        }}
        
        .health-bar {{
            background: #e5e7eb;
            border-radius: 10px;
            height: 30px;
            overflow: hidden;
            margin: 20px 0;
        }}
        
        .health-fill {{
            height: 100%;
            border-radius: 10px;
            transition: width 0.5s ease;
            background: linear-gradient(90deg, #4ade80 0%, #22c55e 100%);
        }}
        
        .health-fill.warning {{
            background: linear-gradient(90deg, #fbbf24 0%, #f59e0b 100%);
        }}
        
        .health-fill.error {{
            background: linear-gradient(90deg, #f87171 0%, #ef4444 100%);
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e5e7eb;
        }}
        
        th {{
            background: #f8fafc;
            font-weight: bold;
            color: #333;
        }}
        
        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 15px;
            font-size: 0.85em;
            font-weight: bold;
        }}
        
        .badge-info {{
            background: #dbeafe;
            color: #1d4ed8;
        }}
        
        .badge-warning {{
            background: #fef3c7;
            color: #b45309;
        }}
        
        .badge-error {{
            background: #fee2e2;
            color: #dc2626;
        }}
        
        .footer {{
            text-align: center;
            color: white;
            margin-top: 40px;
            opacity: 0.8;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🛡️ ScamGuard AI</h1>
            <p class="subtitle">Отчёт работы Telegram бота</p>
            <p style="color: #999; margin-top: 15px;">
                📁 {log_path.name} | 
                📏 {log_path.stat().st_size / 1024:.1f} KB | 
                📊 {stats['total_entries']} записей
            </p>
        </div>
"""
    
    # Bot Status Card
    status_icon = '✅' if stats['startup_info'].get('ready_time') else '❌'
    status_class = 'status-success' if stats['startup_info'].get('ready_time') else 'status-error'
    status_text = 'РАБОТАЕТ' if stats['startup_info'].get('ready_time') else 'НЕ ЗАПУЩЕН'
    
    html += f"""
        <div class="card">
            <h2><span class="icon">🤖</span> Статус бота</h2>
            <div class="status-badge {status_class}">
                {status_icon} {status_text}
            </div>
            <p style="margin-top: 15px; color: #666;">
                <strong>Username:</strong> @{stats['startup_info'].get('username', 'Неизвестно')}<br>
                <strong>Запущен в:</strong> {stats['startup_info'].get('start_time', 'Неизвестно')}<br>
                <strong>Готов к работе:</strong> {stats['startup_info'].get('ready_time', 'Неизвестно')}
            </p>
        </div>
"""
    
    # Statistics Card
    health_score = max(0, 100 - len(stats['errors']) * 10 - len(stats['warnings']) * 5 - stats['conflict_errors'] * 15)
    health_class = 'error' if health_score < 40 else 'warning' if health_score < 80 else ''
    
    html += f"""
        <div class="card">
            <h2><span class="icon">📊</span> Статистика</h2>
            <div class="health-bar">
                <div class="health-fill {health_class}" style="width: {health_score}%"></div>
            </div>
            <p style="text-align: center; font-size: 1.5em; font-weight: bold; color: {'#ef4444' if health_score < 40 else '#f59e0b' if health_score < 80 else '#22c55e'};">
                Здоровье системы: {health_score}/100
            </p>
            <div class="stats-grid">
                <div class="stat-box">
                    <div class="number" style="color: #22c55e;">{stats['success_count']}</div>
                    <div class="label">✅ Успешных</div>
                </div>
                <div class="stat-box">
                    <div class="number" style="color: #ef4444;">{len(stats['errors'])}</div>
                    <div class="label">❌ Ошибок</div>
                </div>
                <div class="stat-box">
                    <div class="number" style="color: #f59e0b;">{len(stats['warnings'])}</div>
                    <div class="label">⚠️ Предупреждений</div>
                </div>
                <div class="stat-box">
                    <div class="number" style="color: #8b5cf6;">{len(stats['user_actions'])}</div>
                    <div class="label">👤 Действий</div>
                </div>
            </div>
        </div>
"""
    
    # Errors Card
    if stats['errors']:
        html += f"""
        <div class="card">
            <h2><span class="icon">🚨</span> Ошибки ({len(stats['errors'])})</h2>
"""
        for error in stats['errors'][:10]:
            error_type = 'Конфликт' if 'Conflict' in error['message'] else 'Сбой'
            html += f"""
            <div class="error-item">
                <div class="time">⏰ {error['time']}</div>
                <div class="message">❌ {error['message'][:100]}</div>
                <div class="solution">💡 Тип: {error_type}</div>
            </div>
"""
        html += """
        </div>
"""
    
    # Log Entries Table
    if logs := analyze_logs(log_file_path):
        html += f"""
        <div class="card">
            <h2><span class="icon">📝</span> Последние события</h2>
            <table>
                <thead>
                    <tr>
                        <th>Время</th>
                        <th>Уровень</th>
                        <th>Сообщение</th>
                    </tr>
                </thead>
                <tbody>
"""
        for log in logs[-20:]:  # Last 20 entries
            badge_class = 'badge-info' if log['level'] == 'INFO' else 'badge-warning' if log['level'] == 'WARNING' else 'badge-error'
            html += f"""
                    <tr>
                        <td>{log['time']}</td>
                        <td><span class="badge {badge_class}">{log['level']}</span></td>
                        <td>{log['message'][:80]}</td>
                    </tr>
"""
        html += """
                </tbody>
            </table>
        </div>
"""
    
    # Footer
    html += f"""
        <div class="footer">
            <p>Создано автоматически | {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}</p>
            <p>🛡️ ScamGuard AI - Защита от мошенников</p>
        </div>
    </div>
</body>
</html>
"""
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    return output_path


def main():
    """Main entry point"""
    # Default log file
    log_file = '/home/exfiltrix/Projects/ScamGuard-AI/logs/bot.log'
    html_output = '/home/exfiltrix/Projects/ScamGuard-AI/logs/bot_report.html'
    
    # Allow custom log file from command line
    if len(sys.argv) > 1:
        log_file = sys.argv[1]
    
    # Check if log file exists
    if not Path(log_file).exists():
        print(f"{Colors.RED}❌ Файл логов не найден: {log_file}{Colors.END}")
        sys.exit(1)
    
    # Parse logs
    logs = analyze_logs(log_file)
    
    if not logs:
        print(f"{Colors.YELLOW}⚠️  Лог файл пустой или не содержит записей{Colors.END}")
        sys.exit(0)
    
    # Get statistics
    stats = get_log_statistics(logs)
    
    # Print beautiful terminal report
    print_beautiful_report(stats, log_file)
    
    # Generate HTML report
    html_path = generate_html_report(stats, log_file, html_output)
    print(f"{Colors.GREEN}📄 HTML отчёт сохранён:{Colors.END} {html_path}")
    print()


if __name__ == '__main__':
    main()

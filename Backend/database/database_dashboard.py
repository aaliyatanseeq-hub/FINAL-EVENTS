# database_dashboard.py
from flask import Flask, render_template_string, request, jsonify
import psycopg2
from psycopg2 import sql
import pandas as pd
from tabulate import tabulate
from datetime import datetime

app = Flask(__name__)

# Database configuration
DB_CONFIG = {
    'dbname': 'event_intelligence',
    'user': 'event_user',
    'password': 'event_password123',
    'host': 'localhost',
    'port': '5432'
}

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>📊 Event Intelligence Database Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        body { background: #f8f9fa; padding: 20px; }
        .card { margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .stat-card { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }
        .table-responsive { max-height: 500px; overflow-y: auto; }
        .badge { font-size: 0.8em; }
        .nav-tabs { margin-bottom: 20px; }
        .query-box { font-family: 'Courier New', monospace; }
        .success { color: #28a745; }
        .warning { color: #ffc107; }
        .danger { color: #dc3545; }
    </style>
</head>
<body>
    <div class="container-fluid">
        <div class="row mb-4">
            <div class="col">
                <h1><i class="fas fa-database"></i> Event Intelligence Database Dashboard</h1>
                <p class="text-muted">PostgreSQL 18 | Database: event_intelligence</p>
            </div>
        </div>

        <!-- Stats Cards -->
        <div class="row mb-4">
            <div class="col-md-2">
                <div class="card stat-card">
                    <div class="card-body">
                        <h5><i class="fas fa-calendar-alt"></i> Events</h5>
                        <h2>{{ stats.events }}</h2>
                    </div>
                </div>
            </div>
            <div class="col-md-2">
                <div class="card stat-card">
                    <div class="card-body">
                        <h5><i class="fas fa-users"></i> Attendees</h5>
                        <h2>{{ stats.attendees }}</h2>
                    </div>
                </div>
            </div>
            <div class="col-md-2">
                <div class="card stat-card">
                    <div class="card-body">
                        <h5><i class="fas fa-history"></i> Searches</h5>
                        <h2>{{ stats.searches }}</h2>
                    </div>
                </div>
            </div>
            <div class="col-md-2">
                <div class="card stat-card">
                    <div class="card-body">
                        <h5><i class="fas fa-retweet"></i> Actions</h5>
                        <h2>{{ stats.actions }}</h2>
                    </div>
                </div>
            </div>
            <div class="col-md-2">
                <div class="card stat-card">
                    <div class="card-body">
                        <h5><i class="fas fa-bolt"></i> Cache</h5>
                        <h2>{{ stats.cache }}</h2>
                    </div>
                </div>
            </div>
            <div class="col-md-2">
                <div class="card stat-card">
                    <div class="card-body">
                        <h5><i class="fas fa-chart-line"></i> Analytics</h5>
                        <h2>{{ stats.analytics }}</h2>
                    </div>
                </div>
            </div>
        </div>

        <!-- Tabs -->
        <ul class="nav nav-tabs" id="dbTabs">
            <li class="nav-item">
                <a class="nav-link active" data-bs-toggle="tab" href="#events">Events</a>
            </li>
            <li class="nav-item">
                <a class="nav-link" data-bs-toggle="tab" href="#attendees">Attendees</a>
            </li>
            <li class="nav-item">
                <a class="nav-link" data-bs-toggle="tab" href="#actions">Actions</a>
            </li>
            <li class="nav-item">
                <a class="nav-link" data-bs-toggle="tab" href="#analytics">Analytics</a>
            </li>
            <li class="nav-item">
                <a class="nav-link" data-bs-toggle="tab" href="#query">SQL Query</a>
            </li>
        </ul>

        <!-- Tab Content -->
        <div class="tab-content">
            <!-- Events Tab -->
            <div class="tab-pane fade show active" id="events">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-calendar-alt"></i> Events Table</h5>
                    </div>
                    <div class="card-body">
                        <div class="table-responsive">
                            {{ events_table|safe }}
                        </div>
                    </div>
                </div>
            </div>

            <!-- Attendees Tab -->
            <div class="tab-pane fade" id="attendees">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-users"></i> Attendees Table</h5>
                    </div>
                    <div class="card-body">
                        <div class="table-responsive">
                            {{ attendees_table|safe }}
                        </div>
                    </div>
                </div>
            </div>

            <!-- Actions Tab -->
            <div class="tab-pane fade" id="actions">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-retweet"></i> User Actions</h5>
                    </div>
                    <div class="card-body">
                        <div class="table-responsive">
                            {{ actions_table|safe }}
                        </div>
                    </div>
                </div>
            </div>

            <!-- Analytics Tab -->
            <div class="tab-pane fade" id="analytics">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-chart-line"></i> Analytics</h5>
                    </div>
                    <div class="card-body">
                        <div class="table-responsive">
                            {{ analytics_table|safe }}
                        </div>
                    </div>
                </div>
            </div>

            <!-- Query Tab -->
            <div class="tab-pane fade" id="query">
                <div class="card">
                    <div class="card-header">
                        <h5><i class="fas fa-terminal"></i> Run SQL Query</h5>
                    </div>
                    <div class="card-body">
                        <form method="POST" action="/execute">
                            <div class="mb-3">
                                <textarea class="form-control query-box" name="sql" rows="4" 
                                          placeholder="SELECT * FROM events LIMIT 10;">SELECT * FROM events LIMIT 10;</textarea>
                            </div>
                            <button type="submit" class="btn btn-primary">
                                <i class="fas fa-play"></i> Execute Query
                            </button>
                        </form>
                        {% if query_result %}
                        <hr>
                        <h6>Results:</h6>
                        <div class="table-responsive">
                            {{ query_result|safe }}
                        </div>
                        {% endif %}
                    </div>
                </div>
            </div>
        </div>

        <!-- Database Info -->
        <div class="card mt-4">
            <div class="card-header">
                <h5><i class="fas fa-info-circle"></i> Database Information</h5>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-6">
                        <p><strong>Connection:</strong> {{ db_info.host }}:{{ db_info.port }}</p>
                        <p><strong>Database:</strong> {{ db_info.dbname }}</p>
                        <p><strong>User:</strong> {{ db_info.user }}</p>
                    </div>
                    <div class="col-md-6">
                        <p><strong>Tables:</strong> {{ db_info.table_count }}</p>
                        <p><strong>Size:</strong> {{ db_info.db_size }}</p>
                        <p><strong>Last Backup:</strong> {{ db_info.last_backup }}</p>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // Auto-refresh every 30 seconds
        setTimeout(() => location.reload(), 30000);
        
        // Tab persistence
        document.addEventListener('DOMContentLoaded', function() {
            var triggerTabList = [].slice.call(document.querySelectorAll('#dbTabs a'))
            triggerTabList.forEach(function (triggerEl) {
                var tabTrigger = new bootstrap.Tab(triggerEl)
                triggerEl.addEventListener('click', function (event) {
                    event.preventDefault()
                    tabTrigger.show()
                })
            })
        });
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get stats
        stats = {}
        tables = ['events', 'attendees', 'search_history', 'user_actions', 'cache', 'analytics']
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                stats[table] = cursor.fetchone()[0]
            except:
                stats[table] = 0
        
        # Get sample data
        try:
            cursor.execute("SELECT * FROM events ORDER BY created_at DESC LIMIT 10")
            events = cursor.fetchall()
            events_df = pd.DataFrame(events, columns=[desc[0] for desc in cursor.description])
            events_table = events_df.to_html(classes='table table-striped', index=False)
        except:
            events_table = '<div class="alert alert-warning">No events found or table does not exist</div>'
        
        try:
            cursor.execute("SELECT username, followers_count, verified, event_name, created_at FROM attendees ORDER BY created_at DESC LIMIT 10")
            attendees = cursor.fetchall()
            attendees_df = pd.DataFrame(attendees, columns=[desc[0] for desc in cursor.description])
            attendees_table = attendees_df.to_html(classes='table table-striped', index=False)
        except:
            attendees_table = '<div class="alert alert-warning">No attendees found or table does not exist</div>'
        
        try:
            cursor.execute("SELECT action_type, target_username, status, created_at FROM user_actions ORDER BY created_at DESC LIMIT 10")
            actions = cursor.fetchall()
            actions_df = pd.DataFrame(actions, columns=[desc[0] for desc in cursor.description])
            actions_table = actions_df.to_html(classes='table table-striped', index=False)
        except:
            actions_table = '<div class="alert alert-warning">No actions found or table does not exist</div>'
        
        try:
            cursor.execute("SELECT * FROM analytics ORDER BY date DESC LIMIT 10")
            analytics = cursor.fetchall()
            analytics_df = pd.DataFrame(analytics, columns=[desc[0] for desc in cursor.description])
            analytics_table = analytics_df.to_html(classes='table table-striped', index=False)
        except:
            analytics_table = '<div class="alert alert-warning">No analytics found or table does not exist</div>'
        
        # Get database info
        try:
            cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'")
            table_count = cursor.fetchone()[0]
        except:
            table_count = 0
        
        try:
            cursor.execute("SELECT pg_size_pretty(pg_database_size('event_intelligence'))")
            db_size = cursor.fetchone()[0]
        except:
            db_size = 'Unknown'
        
        db_info = {
            'host': DB_CONFIG['host'],
            'port': DB_CONFIG['port'],
            'dbname': DB_CONFIG['dbname'],
            'user': DB_CONFIG['user'],
            'table_count': table_count,
            'db_size': db_size,
            'last_backup': 'Never'
        }
        
        cursor.close()
        conn.close()
        
        return render_template_string(HTML_TEMPLATE, 
                                     stats=stats,
                                     events_table=events_table,
                                     attendees_table=attendees_table,
                                     actions_table=actions_table,
                                     analytics_table=analytics_table,
                                     db_info=db_info,
                                     query_result=None)
    
    except Exception as e:
        # Show error page if database connection fails
        error_msg = f'''
        <div class="alert alert-danger">
            <h4><i class="fas fa-exclamation-triangle"></i> Database Connection Error</h4>
            <p><strong>Error:</strong> {str(e)}</p>
            <hr>
            <p><strong>Please check:</strong></p>
            <ul>
                <li>PostgreSQL is running</li>
                <li>Database "event_intelligence" exists</li>
                <li>User credentials in database_dashboard.py are correct</li>
                <li>Connection settings: {DB_CONFIG['host']}:{DB_CONFIG['port']}</li>
            </ul>
            <p><strong>Current Config:</strong></p>
            <pre>{DB_CONFIG}</pre>
        </div>
        '''
        return render_template_string(HTML_TEMPLATE.replace('{{ stats.events }}', '0')
                                                      .replace('{{ stats.attendees }}', '0')
                                                      .replace('{{ stats.searches }}', '0')
                                                      .replace('{{ stats.actions }}', '0')
                                                      .replace('{{ stats.cache }}', '0')
                                                      .replace('{{ stats.analytics }}', '0')
                                                      .replace('{{ events_table|safe }}', error_msg)
                                                      .replace('{{ attendees_table|safe }}', '')
                                                      .replace('{{ actions_table|safe }}', '')
                                                      .replace('{{ analytics_table|safe }}', '')
                                                      .replace('{{ db_info.host }}', DB_CONFIG['host'])
                                                      .replace('{{ db_info.port }}', DB_CONFIG['port'])
                                                      .replace('{{ db_info.dbname }}', DB_CONFIG['dbname'])
                                                      .replace('{{ db_info.user }}', DB_CONFIG['user'])
                                                      .replace('{{ db_info.table_count }}', '0')
                                                      .replace('{{ db_info.db_size }}', 'Unknown')
                                                      .replace('{{ db_info.last_backup }}', 'Never'),
                                     stats={'events': 0, 'attendees': 0, 'searches': 0, 'actions': 0, 'cache': 0, 'analytics': 0},
                                     events_table=error_msg,
                                     attendees_table='',
                                     actions_table='',
                                     analytics_table='',
                                     db_info=DB_CONFIG,
                                     query_result=None)

@app.route('/execute', methods=['POST'])
def execute_query():
    sql = request.form.get('sql', '').strip()
    
    if not sql:
        return "No SQL query provided", 400
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Execute query
        cursor.execute(sql)
        
        if sql.strip().upper().startswith('SELECT'):
            # Fetch results for SELECT
            results = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            
            # Convert to DataFrame for HTML display
            df = pd.DataFrame(results, columns=columns)
            result_html = df.to_html(classes='table table-striped', index=False)
            
            # Add row count
            result_html = f'<div class="alert alert-success">Returned {len(results)} rows</div>' + result_html
        else:
            # For INSERT/UPDATE/DELETE
            conn.commit()
            result_html = f'<div class="alert alert-success">Query executed successfully. Rows affected: {cursor.rowcount}</div>'
        
        cursor.close()
        conn.close()
        
        # Re-render the page with results
        template_with_result = HTML_TEMPLATE.replace('{% if query_result %}', 
                                                     '{% if query_result %}' + result_html + '{% endif %}')
        return render_template_string(template_with_result,
                                     stats={}, events_table='', attendees_table='', 
                                     actions_table='', analytics_table='', db_info={},
                                     query_result=result_html)
        
    except Exception as e:
        error_html = f'<div class="alert alert-danger"><strong>Error:</strong> {str(e)}</div>'
        template_with_error = HTML_TEMPLATE.replace('{% if query_result %}', 
                                                     '{% if query_result %}' + error_html + '{% endif %}')
        return render_template_string(template_with_error,
                                     stats={}, events_table='', attendees_table='', 
                                     actions_table='', analytics_table='', db_info={},
                                     query_result=error_html)

if __name__ == '__main__':
    print("📊 Starting Database Dashboard...")
    print("🌐 Open: http://localhost:5001")
    print("🔄 Auto-refresh every 30 seconds")
    print("⚠️  Note: If you see 'Server is up and running', that's PostgreSQL's interface.")
    print("    Make sure this Flask dashboard is running, not PostgreSQL web interface.")
    app.run(host='127.0.0.1', port=5001, debug=True)
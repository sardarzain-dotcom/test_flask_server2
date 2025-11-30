# Copilot Instructions for test_flask_server2

## Project Overview
This is a multi-application Flask server hosting **two distinct applications**: a web chess game and an ELISA biomarker analysis dashboard. Despite the generic name, this is a sophisticated data science and gaming platform deployed to Google Cloud Run.

## Architecture & Key Components

### 1. Flask Web Server (`app.py`)
- Main entry point with modular route loading
- Attempts to import chess game routes with graceful fallback
- Deployed to Google Cloud Run at `https://testflaskserver2-1010928307866.us-central1.run.app`
- Uses dynamic port binding (`PORT` env var for Cloud Run, defaults to 8000 locally)

### 2. Chess Game System
**Core files**: `chess_game.py`, `chess_pieces.py`, `chess_mechanics.py`, `chess_web.py`
- Complete chess engine with piece validation, special moves (castling, en passant), check/checkmate detection
- Web interface at `/chess`, `/chess/ai`, `/chess/multiplayer` routes
- Global session management for multiplayer games in `chess_web.py`
- Pattern: Object-oriented piece hierarchy with movement validation in individual piece classes

### 3. ELISA Dashboard System
**Main file**: `elisa_test_dashboard.py` (2600+ lines)
- Streamlit-based biomarker analysis platform with advanced statistical features
- Data processing via `elisa_data_processor.py` with pandas/JSON handling
- **Launch pattern**: Use `.bat` files (`Launch_Enhanced_ELISA_Dashboard.bat`) or `streamlit run elisa_test_dashboard.py --server.port 8507`

## Development Workflows

### Running Applications
```bash
# Flask web server (chess + API)
python app.py

# ELISA Dashboard (standalone Streamlit)
streamlit run elisa_test_dashboard.py --server.port 8507

# Chess console version
python chess_console.py

# Use batch launcher on Windows
Launch_Enhanced_ELISA_Dashboard.bat
```

### Data Processing Pattern
ELISA components use **JSON-embedded CSV pattern**: CSV files with JSON metadata columns that get parsed by `ELISADataProcessor` class for biomarker analysis.

### Dependency Management
- **Flask App**: Minimal dependencies (Flask, Werkzeug, gunicorn, python-dotenv)
- **ELISA Dashboard**: Heavy scientific stack (streamlit, pandas, plotly, scipy, numpy)
- **Chess Engine**: Pure Python with optional pygame for GUI
- **Pattern**: Core Flask app stays lightweight, complex features are separate modules

## Project-Specific Conventions

### Port Management
- Flask: 8000 (local), dynamic PORT (Cloud Run)
- Streamlit: 8507-8520 range to avoid conflicts
- **Pattern**: Always specify port explicitly in Streamlit commands to prevent port conflicts

### Session Management
- Chess multiplayer uses global `game_sessions` dict with UUID keys
- Session cleanup after 1 hour via `cleanup_old_sessions()`
- ELISA uses Streamlit's built-in session state for data persistence

### Error Handling
- Chess: Graceful piece movement validation with user feedback
- Flask: Custom 404/500 handlers returning JSON responses
- ELISA: Try/catch with fallback color schemes and data validation

### Deployment Configuration
- **Dockerfile**: Multi-stage with health checks on `/api/health`
- **Procfile**: Simple `gunicorn app:app` for Heroku compatibility
- **Cloud Run**: Uses JSON CMD format for better signal handling

## Key Integration Points

### Chess-Flask Integration
```python
# In app.py - conditional route loading pattern
try:
    from chess_web import add_chess_routes
    add_chess_routes(app)
    CHESS_AVAILABLE = True
except ImportError:
    CHESS_AVAILABLE = False
```

### Data Flow Architecture
1. **ELISA**: CSV upload → JSON parsing → Pandas processing → Plotly visualization → Streamlit dashboard
2. **Chess**: Web UI → Flask routes → Game engine → Session storage → WebSocket-style updates

### Background Processing
- ELISA dashboard runs statistical analysis (scipy.stats) with progress indicators
- Chess AI uses minimax algorithm in separate process threads
- Both handle long-running operations without blocking UI

### Testing & Validation
- **Flask Health Check**: `curl http://localhost:8000/api/health` or visit `/api/status`
- **Chess Engine Test**: Run `python chess_console.py` for quick validation
- **ELISA Data Validation**: Check CSV structure before dashboard launch
- **Port Conflicts**: Use PowerShell port scanning commands in troubleshooting section

## Development Tips

### When Working on Chess Components
- Test both console (`chess_console.py`) and web interfaces
- Piece movement logic is in individual piece classes, not the board
- Multiplayer state is ephemeral (in-memory dict), not persistent

### When Working on ELISA Dashboard
- Use `elisa_test_dashboard.py` as the main file (not the many backup versions)
- Data validation happens in processor classes before visualization
- Color schemes and animations are deeply integrated - changes affect multiple visualization types

### Common Pitfalls
- Don't run Streamlit on default port 8501 (conflicts with other instances)
- Chess game imports can fail silently - check `CHESS_AVAILABLE` flag in templates
- ELISA data expects specific CSV structure with JSON columns - validate early

## Troubleshooting & Debugging

### Streamlit Server Issues
```powershell
# Check running Python processes
Get-Process python* -ErrorAction SilentlyContinue | Select-Object Id, ProcessName, CPU

# Test port availability (common ports: 8507, 8510-8520)
@(8507, 8510, 8515, 8517, 8520) | ForEach-Object { 
    try { Invoke-WebRequest -Uri "http://localhost:$_" -TimeoutSec 2 } 
    catch { Write-Host "Port $_ available" } 
}

# Kill stuck Streamlit processes
Get-Process python* | Where-Object {$_.ProcessName -like "*python*"} | Stop-Process -Force
```

### Development Environment Setup
- **Python Environment**: Requires Python 3.8+ with pandas, streamlit, plotly, scipy
- **Port Strategy**: Use 8507 as primary, fall back to 8510-8520 range
- **Windows Automation**: Batch files handle environment activation and port selection automatically

### ELISA Dashboard Specific Issues
- **Data Structure**: CSV files must have JSON columns for biomarker metadata
- **Memory Usage**: Large datasets (>1000 rows) should disable animations
- **Session State**: Streamlit session state persists data - clear browser cache if issues occur
- **Color Schemes**: Fallback color handling prevents crashes with missing plotly themes

### Chess Game Debugging
- **Import Failures**: `chess_web.py` imports gracefully fail - check `CHESS_AVAILABLE` in Flask app
- **Session Cleanup**: Multiplayer sessions auto-expire after 1 hour
- **Piece Validation**: Movement logic is in individual piece classes, not board class
- **Console vs Web**: Test chess logic in console version first before debugging web interface

## File Organization Logic
- `*_test_*`: Current production versions
- `*_backup*`: Version backups with timestamps
- `Launch_*.bat`: Windows automation scripts
- `*_SUMMARY.md`: Implementation documentation
- `*_GUIDE.md`: User documentation
# Create .env file template
# RTGS Lab Tools Installation Script
# Works on Windows (Git Bash/WSL), macOS, and Linux

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "\n${BLUE}================================${NC}"
    echo -e "${BLUE}  RTGS Lab Tools Installation${NC}"
    echo -e "${BLUE}================================${NC}\n"
}

# Detect operating system
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
    elif [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        OS="windows"
    else
        OS="unknown"
    fi
    print_status "Detected OS: $OS"
}

# Check if Python is available
check_python() {
    print_status "Checking Python installation..."
    
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        print_error "Python is not installed or not in PATH"
        print_error "Please install Python 3.10+ before running this script"
        exit 1
    fi
    
    # Check Python version
    PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
    print_success "Found Python $PYTHON_VERSION at $(which $PYTHON_CMD)"
    
    # Verify minimum version (3.10+)
    PYTHON_MAJOR=$($PYTHON_CMD -c "import sys; print(sys.version_info.major)")
    PYTHON_MINOR=$($PYTHON_CMD -c "import sys; print(sys.version_info.minor)")
    
    if [[ $PYTHON_MAJOR -lt 3 ]] || [[ $PYTHON_MAJOR -eq 3 && $PYTHON_MINOR -lt 10 ]]; then
        print_error "Python 3.10 or higher is required. Found Python $PYTHON_VERSION"
        exit 1
    fi
}

# Check if pip is available
check_pip() {
   print_status "Checking pip installation..."
   
   if command -v pip3 &> /dev/null; then
       PIP_CMD="pip3"
   elif command -v pip &> /dev/null; then
       PIP_CMD="pip"
   else
       print_error "pip is not installed or not in PATH"
       print_error "Please install pip before running this script"
       exit 1
   fi
   
   print_success "Found pip at $(which $PIP_CMD)"
}

# Check if uv is available, install if not
check_uv() {
   print_status "Checking uv installation..."
   
   if command -v uv &> /dev/null; then
       UV_VERSION=$(uv --version)
       print_success "Found uv: $UV_VERSION"
   else
       print_status "uv not found. Installing uv..."
       
       if [[ "$OS" == "windows" ]]; then
           # Windows installation using PowerShell
           if command -v powershell &> /dev/null; then
               powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
               # Add to PATH for current session
               export PATH="$HOME/.local/bin:$PATH"
           else
               print_error "PowerShell not found. Cannot install uv automatically on Windows."
               print_error "Please install uv manually: https://docs.astral.sh/uv/getting-started/installation/"
               exit 1
           fi
       else
           # Linux and macOS installation
           if command -v curl &> /dev/null; then
               curl -LsSf https://astral.sh/uv/install.sh | sh
               # Source the shell profile to get uv in PATH
               export PATH="$HOME/.local/bin:$PATH"
           elif command -v wget &> /dev/null; then
               wget -qO- https://astral.sh/uv/install.sh | sh
               export PATH="$HOME/.local/bin:$PATH"
           else
               print_error "Neither curl nor wget found. Cannot install uv automatically."
               print_error "Please install uv manually: https://docs.astral.sh/uv/getting-started/installation/"
               exit 1
           fi
       fi
       
       # Verify installation
       if command -v uv &> /dev/null; then
           UV_VERSION=$(uv --version)
           print_success "uv installed successfully: $UV_VERSION"
       else
           print_error "Failed to install uv. Please install manually."
           print_error "Installation guide: https://docs.astral.sh/uv/getting-started/installation/"
           exit 1
       fi
   fi
}

# Initialize git submodules
init_submodules() {
    print_status "Checking git submodules..."
    
    if [[ ! -d ".git" ]]; then
        print_warning "Not a git repository. Skipping submodule initialization."
        return
    fi
    
    # Check if there are any submodules defined
    if [[ -f ".gitmodules" ]]; then
        print_status "Initializing and updating git submodules..."
        git submodule update --init --recursive
        print_success "Git submodules updated"
    else
        print_status "No submodules found in repository"
    fi
}

# Create virtual environment
create_venv() {
    print_status "Creating virtual environment..."
    
    # Always create venv in the project root directory
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    VENV_PATH="$SCRIPT_DIR/venv"
    
    if [[ -d "$VENV_PATH" ]]; then
        print_warning "Virtual environment already exists. Removing old one..."
        rm -rf "$VENV_PATH"
    fi
    
    $PYTHON_CMD -m venv "$VENV_PATH"
    print_success "Virtual environment created: $VENV_PATH"
}

# Activate virtual environment
activate_venv() {
    print_status "Activating virtual environment..."
    
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    
    if [[ "$OS" == "windows" ]]; then
        source "$SCRIPT_DIR/venv/Scripts/activate"
    else
        source "$SCRIPT_DIR/venv/bin/activate"
    fi
    
    print_success "Virtual environment activated"
    print_status "Python path: $(which python)"
    print_status "Pip path: $(which pip)"
}

# Upgrade pip
upgrade_pip() {
    print_status "Upgrading pip..."
    python -m pip install --upgrade pip
    print_success "Pip upgraded successfully"
}

# Install package in development mode
install_package() {
    print_status "Installing RTGS Lab Tools in development mode..."
    
    # Install in editable mode with all dependencies
    # Use quotes for zsh compatibility on macOS
    python -m pip install -e ".[all]"
    
    print_success "Package installed successfully"
}

# Run setup credentials command
run_setup_credentials() {
    print_status "Running setup credentials script..."
    
    if command -v python &> /dev/null && python -c "import rtgs_lab_tools" 2>/dev/null; then
        python -m rtgs_lab_tools.cli sensing-data extract --setup-credentials || true
        print_success "Setup credentials command executed"
    else
        print_warning "Could not run setup credentials command. Package may not be properly installed."
    fi
}

# Google Earth Engine Authentication
auth_gee() {
    if command -v python &> /dev/null && python -c "import rtgs_lab_tools" 2>/dev/null; then
        python -c "import ee; ee.Authenticate()"
        print_success "GEE Authentication is completed"
    else
        print_warning "Could not run setup credentials command. Package may not be properly installed."
    fi
}

# Configure Claude Desktop MCP servers
configure_claude_desktop() {
    print_status "Configuring Claude Desktop MCP servers..."
    
    # Get absolute path to repository
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    
    # Determine Claude Desktop config path based on OS
    case "$OS" in
        "macos")
            CLAUDE_CONFIG_DIR="$HOME/Library/Application Support/Claude"
            CLAUDE_CONFIG_FILE="$CLAUDE_CONFIG_DIR/claude_desktop_config.json"
            PYTHON_PATH="$SCRIPT_DIR/venv/bin/python"
            PARTICLE_PATH="$SCRIPT_DIR/src/rtgs_lab_tools/mcp_server/particle-mcp-server/"
            ;;
        "windows")
            CLAUDE_CONFIG_DIR="$USERPROFILE/AppData/Roaming/Claude"
            CLAUDE_CONFIG_FILE="$CLAUDE_CONFIG_DIR/claude_desktop_config.json"
            PYTHON_PATH="$SCRIPT_DIR/venv/Scripts/python.exe"
            # Convert Windows path format
            PARTICLE_PATH="$(cygpath -w "$SCRIPT_DIR/src/rtgs_lab_tools/mcp_server/particle-mcp-server/" 2>/dev/null || echo "$SCRIPT_DIR/src/rtgs_lab_tools/mcp_server/particle-mcp-server/")"
            ;;
        "linux")
            CLAUDE_CONFIG_DIR="$HOME/.config/Claude"
            CLAUDE_CONFIG_FILE="$CLAUDE_CONFIG_DIR/claude_desktop_config.json"
            PYTHON_PATH="$SCRIPT_DIR/venv/bin/python"
            PARTICLE_PATH="$SCRIPT_DIR/src/rtgs_lab_tools/mcp_server/particle-mcp-server/"
            ;;
        *)
            print_warning "Unknown OS. Skipping Claude Desktop MCP configuration."
            return
            ;;
    esac
    
    # Check if Claude Desktop is installed by looking for the config directory
    if [[ ! -d "$CLAUDE_CONFIG_DIR" ]]; then
        print_warning "Claude Desktop not found (directory doesn't exist: $CLAUDE_CONFIG_DIR)"
        print_warning "Skipping Claude Desktop MCP configuration. Install Claude Desktop first if you want MCP integration."
        return
    fi
    
    # Create or update claude_desktop_config.json
    if [[ -f "$CLAUDE_CONFIG_FILE" ]]; then
        print_status "Backing up existing Claude Desktop config..."
        cp "$CLAUDE_CONFIG_FILE" "${CLAUDE_CONFIG_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
    fi
    
    # Generate the configuration
    print_status "Writing Claude Desktop MCP configuration..."
    
    if [[ "$OS" == "windows" ]]; then
        # Windows format with escaped backslashes
        cat > "$CLAUDE_CONFIG_FILE" << EOF
{
  "mcpServers": {
    "particle": {
      "command": "uv",
      "args": [
        "--directory",
        "${PARTICLE_PATH//\//\\\\}",
        "run",
        "particle.py"
      ]
    },
    "rtgs_lab_tools": {
      "command": "${PYTHON_PATH//\//\\\\}",
      "args": ["-m", "rtgs_lab_tools.mcp_server.rtgs_lab_tools_mcp_server"]
    }
  }
}
EOF
    else
        # macOS and Linux format with forward slashes
        cat > "$CLAUDE_CONFIG_FILE" << EOF
{
  "mcpServers": {
    "particle": {
      "command": "uv",
      "args": [
        "--directory",
        "$PARTICLE_PATH",
        "run",
        "particle.py"
      ]
    },
    "rtgs_lab_tools": {
      "command": "$PYTHON_PATH",
      "args": ["-m", "rtgs_lab_tools.mcp_server.rtgs_lab_tools_mcp_server"]
    }
  }
}
EOF
    fi
    
    if [[ $? -eq 0 ]]; then
        print_success "Claude Desktop MCP configuration created: $CLAUDE_CONFIG_FILE"
        print_status "Restart Claude Desktop to load the new MCP servers"
    else
        print_error "Failed to create Claude Desktop MCP configuration"
    fi
}

# Check if required directories exist
check_directories() {
    print_status "Checking project structure..."
    
    REQUIRED_DIRS=("src" "tests")
    REQUIRED_FILES=("pyproject.toml" "README.md")
    
    for dir in "${REQUIRED_DIRS[@]}"; do
        if [[ ! -d "$dir" ]]; then
            print_error "Required directory not found: $dir"
            print_error "Please run this script from the project root directory"
            exit 1
        fi
    done
    
    for file in "${REQUIRED_FILES[@]}"; do
        if [[ ! -f "$file" ]]; then
            print_error "Required file not found: $file"
            print_error "Please run this script from the project root directory"
            exit 1
        fi
    done
    
    print_success "Project structure verified"
}

# Display next steps
show_next_steps() {
    echo -e "\n${GREEN}================================${NC}"
    echo -e "${GREEN}  Installation Complete!${NC}"
    echo -e "${GREEN}================================${NC}\n"
    
    echo -e "${YELLOW}Next Steps:${NC}"
    echo -e "1. ${BLUE}Activate the virtual environment:${NC}"
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    if [[ "$OS" == "windows" ]]; then
        echo -e "   ${BLUE}source $SCRIPT_DIR/venv/Scripts/activate${NC}"
    else
        echo -e "   ${BLUE}source $SCRIPT_DIR/venv/bin/activate${NC}"
    fi
    
    echo -e "\n2. ${BLUE}Configure your credentials:${NC}"
    echo -e "   Edit the .env file with your actual database and API credentials:"
    echo -e "   ${BLUE}nano .env${NC}  (or use your preferred editor)"
    
    echo -e "\n3. ${BLUE}Required credentials to populate in .env:${NC}"
    echo -e "   • ${YELLOW}Database credentials${NC} (DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD)"
    echo -e "   • ${YELLOW}Particle access token${NC} (PARTICLE_ACCESS_TOKEN)"
    echo -e "   • ${YELLOW}Climate Data Store API key${NC} (CDS_API_KEY)"
    
    echo -e "\n4. ${BLUE}Test the installation:${NC}"
    echo -e "   ${BLUE}rtgs --help${NC}"
    
    echo -e "\n5. ${BLUE}List available projects:${NC}"
    echo -e "   ${BLUE}rtgs sensing-data list-projects${NC}"
    
    echo -e "\n${BLUE}Documentation:${NC}"
    echo -e "   • Check the README.md for detailed usage instructions"
    echo -e "   • See tests/ directory for usage examples"
}

# Main installation process
main() {
    print_header
    
    # Change to script directory to ensure we're in the project root
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    cd "$SCRIPT_DIR"
    
    detect_os
    check_directories
    init_submodules
    check_python
    check_pip
    check_uv
    create_venv
    activate_venv
    upgrade_pip
    install_package
    run_setup_credentials
    auth_gee
    configure_claude_desktop

    show_next_steps
}

# Handle script interruption
trap 'print_error "Installation interrupted. You may need to clean up manually."; exit 1' INT TERM

# Run main function
main "$@"

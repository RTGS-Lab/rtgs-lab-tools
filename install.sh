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
        print_error "Please install Python 3.8+ before running this script"
        exit 1
    fi
    
    # Check Python version
    PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
    print_success "Found Python $PYTHON_VERSION at $(which $PYTHON_CMD)"
    
    # Verify minimum version (3.8+)
    PYTHON_MAJOR=$($PYTHON_CMD -c "import sys; print(sys.version_info.major)")
    PYTHON_MINOR=$($PYTHON_CMD -c "import sys; print(sys.version_info.minor)")
    
    if [[ $PYTHON_MAJOR -lt 3 ]] || [[ $PYTHON_MAJOR -eq 3 && $PYTHON_MINOR -lt 8 ]]; then
        print_error "Python 3.8 or higher is required. Found Python $PYTHON_VERSION"
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
    
    VENV_NAME="venv"
    
    if [[ -d "$VENV_NAME" ]]; then
        print_warning "Virtual environment already exists. Removing old one..."
        rm -rf "$VENV_NAME"
    fi
    
    $PYTHON_CMD -m venv "$VENV_NAME"
    print_success "Virtual environment created: $VENV_NAME"
}

# Activate virtual environment
activate_venv() {
    print_status "Activating virtual environment..."
    
    if [[ "$OS" == "windows" ]]; then
        source "venv/Scripts/activate"
    else
        source "venv/bin/activate"
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
    python -m pip install -e .[all]
    
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
    if [[ "$OS" == "windows" ]]; then
        echo -e "   ${BLUE}source .venv/Scripts/activate${NC}"
    else
        echo -e "   ${BLUE}source .venv/bin/activate${NC}"
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
    
    show_next_steps
}

# Handle script interruption
trap 'print_error "Installation interrupted. You may need to clean up manually."; exit 1' INT TERM

# Run main function
main "$@"
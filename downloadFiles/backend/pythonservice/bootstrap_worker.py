import os
import sys

# 1. Localizar onde está o executável do Python
bin_dir = os.path.dirname(sys.executable)
if bin_dir.startswith("\\\\?\\"):
    bin_dir = bin_dir[4:]

# 2. Forçar o Windows a aceitar DLLs desta pasta (Correção do Erro ctypes)
if os.path.isdir(bin_dir):
    os.add_dll_directory(bin_dir)

# 3. Configurar caminhos de busca
sys.path.insert(0, os.getcwd()) # Pasta do serviço
sys.path.insert(0, os.path.join(bin_dir, "Lib", "site-packages"))
sys.path.insert(0, os.path.join(bin_dir, "python312.zip"))

# 4. Iniciar o Worker
from worker.worker import _main_loop

if __name__ == "__main__":
    _main_loop()

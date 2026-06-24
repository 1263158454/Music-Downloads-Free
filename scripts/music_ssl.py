#!/home/admin/.venv/bin/python
"""SSL patch wrapper — 解决系统CA证书过期问题"""
import ssl, certifi, sys, os

# Patch SSL to use certifi's up-to-date CA bundle
ssl._create_default_https_context = lambda: ssl.create_default_context(cafile=certifi.where())

# Run the real script
real_script = os.path.join(os.path.dirname(__file__), 'music.py')
sys.argv[0] = real_script
with open(real_script) as f:
    exec(compile(f.read(), real_script, 'exec'), {'__name__': '__main__', '__file__': real_script})

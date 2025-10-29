import asyncio, json, pathlib, sys, os

# Ensure project root is on sys.path so `src` package imports work when run as a script
sys.path.insert(0, os.getcwd())

print('TEST SCRIPT START', flush=True)

from src.utils.celsius_auth import CelsiusAuth

DATA_DIR = pathlib.Path('.')

async def test_login():
    auth = CelsiusAuth(DATA_DIR)
    await auth.initialize()
    success, result = await auth.authenticate("cllusion001", "T3qy22ny*@dyu0ppn*pG")
    print('AUTH SUCCESS:', success)
    print('RESULT:', result)

    # show auth file contents after possible upgrade
    auth_file = DATA_DIR / 'celsius_auth.json'
    if auth_file.exists():
        print('\n--- celsius_auth.json (post-auth) ---')
        print(auth_file.read_text(encoding='utf-8'))
    else:
        print('Auth file not found at', auth_file)

if __name__ == '__main__':
    asyncio.run(test_login())

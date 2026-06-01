import shutil, pathlib, sys

def clean_chroma():
    """Delete the Chroma DB folder if present."""
    chroma_path = pathlib.Path('data/chroma_db')
    if chroma_path.exists():
        try:
            shutil.rmtree(chroma_path)
            print('Deleted Chroma DB folder at', chroma_path)
        except Exception as e:
            print('Failed to delete Chroma DB folder:', e)
            sys.exit(1)
    else:
        print('No Chroma DB folder found at', chroma_path)

if __name__ == "__main__":
    clean_chroma()

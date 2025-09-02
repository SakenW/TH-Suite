import sys
import os

# Add the core package to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../packages/core/src'))

# Now import and run the main module
if __name__ == "__main__":
    import main
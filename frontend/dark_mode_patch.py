import re

path = "c:/Users/User/.gemini/antigravity/scratch/gorkem-gonen-hedef/frontend/src/App.jsx"
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

replacements = {
    r'\bbg-white\b(?! dark:bg-slate-900)': 'bg-white dark:bg-slate-900',
    r'\bbg-slate-50\b(?! dark:bg-slate-950)': 'bg-slate-50 dark:bg-slate-950',
    r'\bbg-slate-100\b(?! dark:bg-slate-800)': 'bg-slate-100 dark:bg-slate-800',
    
    r'\bborder-slate-200\b(?! dark:border-slate-800)': 'border-slate-200 dark:border-slate-800',
    r'\bborder-slate-300\b(?! dark:border-slate-700)': 'border-slate-300 dark:border-slate-700',
    
    r'\btext-slate-800\b(?! dark:text-slate-200)': 'text-slate-800 dark:text-slate-200',
    r'\btext-slate-900\b(?! dark:text-slate-100)': 'text-slate-900 dark:text-slate-100',
    r'\btext-slate-700\b(?! dark:text-slate-300)': 'text-slate-700 dark:text-slate-300',
    r'\btext-slate-600\b(?! dark:text-slate-400)': 'text-slate-600 dark:text-slate-400',
    r'\btext-slate-500\b(?! dark:text-slate-400)': 'text-slate-500 dark:text-slate-400',
}

for k, v in replacements.items():
    text = re.sub(k, v, text)

with open(path, "w", encoding="utf-8") as f:
    f.write(text)
print("Dark mode classes injected successfully.")

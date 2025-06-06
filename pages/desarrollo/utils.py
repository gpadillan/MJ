import pandas as pd

def procesar_kpis_cierre(df: pd.DataFrame) -> dict:
    df = df.copy()
    df.columns = df.columns.str.strip().str.upper()

    df['CONSECUCIÓN GE'] = df['CONSECUCIÓN GE'].astype(str).str.strip().str.upper()
    df['INAPLICACIÓN GE'] = df['INAPLICACIÓN GE'].astype(str).str.strip().str.upper()
    df['DEVOLUCIÓN GE'] = df['DEVOLUCIÓN GE'].astype(str).str.strip().str.upper()
    df['PRÁCTCAS/GE'] = df['PRÁCTCAS/GE'].astype(str).str.strip().str.upper()
    df['EMPRESA PRÁCT.'] = df['EMPRESA PRÁCT.'].astype(str).str.strip().str.upper()
    df['EMPRESA GE'] = df['EMPRESA GE'].astype(str).str.strip().str.upper()

    df['CONSECUCIÓN_BOOL'] = df['CONSECUCIÓN GE'] == 'TRUE'
    df['INAPLICACIÓN_BOOL'] = df['INAPLICACIÓN GE'] == 'TRUE'

    df['PRACTICAS_BOOL'] = (
        (df['PRÁCTCAS/GE'] == 'GE') &
        (~df['EMPRESA PRÁCT.'].isin(['', 'NO ENCONTRADO'])) &
        (df['CONSECUCIÓN GE'] == 'FALSE') &
        (df['DEVOLUCIÓN GE'] == 'FALSE') &
        (df['INAPLICACIÓN GE'] == 'FALSE')
    )

    return {
        "CONSECUCIÓN": int(df['CONSECUCIÓN_BOOL'].sum()),
        "INAPLICACIÓN": int(df['INAPLICACIÓN_BOOL'].sum()),
        "Alumnado total en PRÁCTICAS": int(df['EMPRESA GE'][~df['EMPRESA GE'].isin(['', 'NO ENCONTRADO'])].shape[0]),
        "Prácticas actuales": int(df['PRACTICAS_BOOL'].sum())
    }

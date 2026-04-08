"""limpar_antigos.py — Remove registros com mais de 30 dias do Supabase."""
import httpx
from datetime import date, timedelta

SUPABASE_URL = "https://wzjdthcxlsopmqcwtvla.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Ind6amR0aGN4bHNvcG1xY3d0dmxhIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NzUzNjY2MywiZXhwIjoyMDczMTEyNjYzfQ.ZRXuEULiCpkIYDhspjYd1dadql4AwMnygGzr6D6Ts0Q"
HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
}


def limpar() -> None:
    """Deleta registros mais antigos que 30 dias em todas as tabelas relevantes."""
    data_corte = (date.today() - timedelta(days=30)).isoformat()
    tabelas = ["we_modelos", "we_leituras", "we_previsoes", "we_odds"]

    print(f"Limpando registros anteriores a {data_corte}...")

    for tabela in tabelas:
        try:
            r = httpx.delete(
                f"{SUPABASE_URL}/rest/v1/{tabela}?data_alvo=lt.{data_corte}",
                headers=HEADERS,
                timeout=30,
            )
            print(f"  {tabela}: status {r.status_code}")
        except Exception as e:
            print(f"  {tabela}: ERRO — {e}")

    print("Limpeza concluida!")


if __name__ == "__main__":
    limpar()

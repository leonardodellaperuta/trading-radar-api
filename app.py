from flask import Flask, jsonify
from flask_cors import CORS
import requests
import time
import random

app = Flask(__name__)
CORS(app)

# Headers realistici che simulano un browser Chrome reale
def get_headers():
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9,it;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0',
        'Referer': 'https://finance.yahoo.com/',
    }

# Sessione persistente con cookie — simula navigazione reale
session = requests.Session()

def warm_up_session():
    """Visita Yahoo Finance per ottenere cookie reali prima delle richieste dati"""
    try:
        session.get(
            'https://finance.yahoo.com',
            headers=get_headers(),
            timeout=10
        )
    except Exception:
        pass

# Warm up all'avvio
warm_up_session()

def fetch_yahoo(ticker, interval='1d', range_='3mo', retries=3):
    """Fetch dati Yahoo Finance con retry e delay randomico"""
    urls = [
        f'https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval={interval}&range={range_}',
        f'https://query2.finance.yahoo.com/v8/finance/chart/{ticker}?interval={interval}&range={range_}',
    ]
    
    for attempt in range(retries):
        for url in urls:
            try:
                # Delay randomico per sembrare umano
                if attempt > 0:
                    time.sleep(random.uniform(1.0, 2.5))
                
                r = session.get(
                    url,
                    headers=get_headers(),
                    timeout=12
                )
                
                if r.status_code == 200:
                    data = r.json()
                    if data.get('chart', {}).get('result'):
                        return data
                        
                elif r.status_code == 429:
                    # Rate limited — aspetta di più
                    time.sleep(random.uniform(3.0, 6.0))
                    
            except Exception:
                continue
    
    return None

@app.route('/')
def home():
    return jsonify({
        'status': 'Trading Radar API online',
        'version': '2.0',
        'endpoints': ['/daily/<ticker>', '/intraday/<ticker>', '/scan']
    })

@app.route('/daily/<ticker>')
def daily(ticker):
    data = fetch_yahoo(ticker, interval='1d', range_='3mo')
    if not data:
        return jsonify({'error': 'No data'}), 404
    return jsonify(data)

@app.route('/intraday/<ticker>')
def intraday(ticker):
    # Prima prova 15min, fallback su 30min
    data = fetch_yahoo(ticker, interval='15m', range_='2d')
    if not data:
        data = fetch_yahoo(ticker, interval='30m', range_='5d')
    if not data:
        return jsonify({'error': 'No data'}), 404
    return jsonify(data)

@app.route('/scan')
def scan():
    """Scansione completa — daily per tutti, intraday per i ticker richiesti"""
    tickers = [
        # Mega cap
        'TSLA','NVDA','AMD','META','AMZN','GOOGL','MSFT','AAPL','NFLX','INTC','ARM','QCOM','NIO','BABA',
        # Growth
        'PLTR','CRWD','NET','SNOW','DDOG','MDB','RBLX','SOFI','UPST','AFRM','HOOD','LC','DKNG',
        'ROKU','ZM','LYFT','UBER','DASH','PATH','SMCI','FUTU','OPEN','RIVN','SPCE',
        'ASTS','RKLB','JOBY','ACHR','LUNR','SOUN','IONQ',
        # Biotech
        'MRNA','NVAX','BNTX','CRSP','BEAM','EDIT','NTLA','RXRX','ARWR','EXEL','FOLD','FATE','RARE',
        # Crypto-equity
        'COIN','MSTR','RIOT','MARA','CLSK','HUT','CIFR','WULF','IREN',
        # Energia
        'PLUG','FCEL','BE','ENPH','SEDG','RUN','NOVA',
        # Meme
        'GME','AMC','NKLA','GOEV',
        # Crypto
        'BTC-USD','ETH-USD','SOL-USD','XRP-USD','ADA-USD','DOGE-USD','LINK-USD','AVAX-USD','DOT-USD'
    ]

    results = []
    
    for ticker in tickers:
        try:
            # Daily
            d_data = fetch_yahoo(ticker, '1d', '3mo')
            if not d_data or not d_data.get('chart', {}).get('result'):
                continue
                
            dr = d_data['chart']['result'][0]
            dq = dr['indicators']['quote'][0]
            closes = [p for p in (dq.get('close') or []) if p is not None]
            highs  = [p for p in (dq.get('high')  or []) if p is not None]
            lows   = [p for p in (dq.get('low')   or []) if p is not None]
            vols   = [p for p in (dq.get('volume') or []) if p is not None]
            
            if len(closes) < 15:
                continue

            # Intraday 15min con fallback 30min
            i_closes, i_highs, i_lows, i_vols = [], [], [], []
            
            i_data = fetch_yahoo(ticker, '15m', '2d')
            if not i_data:
                i_data = fetch_yahoo(ticker, '30m', '5d')
                
            if i_data and i_data.get('chart', {}).get('result'):
                ir = i_data['chart']['result'][0]
                iq = ir['indicators']['quote'][0]
                ic = iq.get('close') or []
                ih = iq.get('high')  or []
                il = iq.get('low')   or []
                iv = iq.get('volume') or []
                valid = [i for i, v in enumerate(ic) if v is not None]
                last26 = valid[-26:]
                i_closes = [ic[i] for i in last26]
                i_highs  = [ih[i] if i < len(ih) and ih[i] else ic[i] for i in last26]
                i_lows   = [il[i] if i < len(il) and il[i] else ic[i] for i in last26]
                i_vols   = [iv[i] if i < len(iv) else 0 for i in last26]

            results.append({
                'ticker': ticker,
                'daily': {
                    'closes': closes[-30:],
                    'highs':  highs[-30:],
                    'lows':   lows[-30:],
                    'vols':   vols[-30:]
                },
                'intraday': {
                    'closes': i_closes,
                    'highs':  i_highs,
                    'lows':   i_lows,
                    'vols':   i_vols
                } if i_closes else None
            })

            # Pausa gentile tra i ticker
            time.sleep(random.uniform(0.2, 0.5))

        except Exception:
            continue

    return jsonify({'results': results, 'count': len(results)})

if __name__ == '__main__':
    app.run(debug=False)

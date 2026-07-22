"""
Çark (Roulette) Komponenti
--------------------------
CSS/JS tabanlı interaktif dönen çark.
"""

import random
import streamlit.components.v1 as components


def create_wheel_html(items: list[dict], wheel_id: str = "wheel") -> str:
    """
    Dönen çark için HTML/CSS/JS oluştur.
    
    Args:
        items: Çarkta gösterilecek içerikler (max 8)
        wheel_id: Benzersiz çark ID'si
    
    Returns:
        HTML string
    """
    # Maksimum 8 içerik
    items = items[:8]
    num_items = len(items)
    
    if num_items == 0:
        return "<p>Gösterilecek içerik yok</p>"
    
    # Renk paleti
    colors = [
        "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4",
        "#FFEAA7", "#DDA0DD", "#98D8C8", "#F7DC6F",
    ]
    
    # Çark dilimlerini oluştur
    slice_angle = 360 / num_items
    slices_css = ""
    slices_data = []
    
    for i, item in enumerate(items):
        start_angle = i * slice_angle
        color = colors[i % len(colors)]
        title = item.get("title", "?")[:15]  # Maksimum 15 karakter
        
        slices_data.append({
            "title": item.get("title", "Bilinmiyor"),
            "id": item.get("id"),
            "poster_url": item.get("poster_url", ""),
            "overview": item.get("overview", "Açıklama yok.")[:200],
            "vote_average": item.get("vote_average", 0),
        })
        
        slices_css += f"""
            .slice-{i} {{
                background: conic-gradient(
                    from {start_angle}deg,
                    {color} 0deg,
                    {color} {slice_angle}deg,
                    transparent {slice_angle}deg
                );
            }}
        """
    
    # JSON data for JS
    import json
    items_json = json.dumps(slices_data, ensure_ascii=False)
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: transparent;
                display: flex;
                flex-direction: column;
                align-items: center;
                padding: 20px;
            }}
            
            .wheel-container {{
                position: relative;
                width: 320px;
                height: 320px;
                margin-bottom: 20px;
            }}
            
            .wheel {{
                width: 100%;
                height: 100%;
                border-radius: 50%;
                position: relative;
                overflow: hidden;
                box-shadow: 
                    0 0 0 8px #2c3e50,
                    0 0 0 12px #34495e,
                    0 0 30px rgba(0,0,0,0.3);
                transition: transform 4s cubic-bezier(0.17, 0.67, 0.12, 0.99);
            }}
            
            .wheel-inner {{
                width: 100%;
                height: 100%;
                position: relative;
            }}
            
            .slice {{
                position: absolute;
                width: 100%;
                height: 100%;
                border-radius: 50%;
            }}
            
            {slices_css}
            
            .slice-label {{
                position: absolute;
                left: 50%;
                top: 15%;
                transform-origin: 0 150px;
                color: #2c3e50;
                font-weight: bold;
                font-size: 11px;
                text-shadow: 1px 1px 2px rgba(255,255,255,0.8);
                white-space: nowrap;
                max-width: 80px;
                overflow: hidden;
                text-overflow: ellipsis;
            }}
            
            .center-circle {{
                position: absolute;
                width: 60px;
                height: 60px;
                background: linear-gradient(145deg, #2c3e50, #1a252f);
                border-radius: 50%;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-size: 24px;
                box-shadow: 0 4px 15px rgba(0,0,0,0.3);
                z-index: 10;
            }}
            
            .pointer {{
                position: absolute;
                top: -15px;
                left: 50%;
                transform: translateX(-50%);
                width: 0;
                height: 0;
                border-left: 20px solid transparent;
                border-right: 20px solid transparent;
                border-top: 35px solid #e74c3c;
                filter: drop-shadow(0 3px 5px rgba(0,0,0,0.3));
                z-index: 20;
            }}
            
            .spin-btn {{
                background: linear-gradient(145deg, #e74c3c, #c0392b);
                color: white;
                border: none;
                padding: 15px 50px;
                font-size: 18px;
                font-weight: bold;
                border-radius: 50px;
                cursor: pointer;
                box-shadow: 0 6px 20px rgba(231, 76, 60, 0.4);
                transition: all 0.3s ease;
                margin-bottom: 20px;
            }}
            
            .spin-btn:hover {{
                transform: translateY(-2px);
                box-shadow: 0 8px 25px rgba(231, 76, 60, 0.5);
            }}
            
            .spin-btn:active {{
                transform: translateY(1px);
            }}
            
            .spin-btn:disabled {{
                background: #95a5a6;
                cursor: not-allowed;
                box-shadow: none;
            }}
            
            .result-card {{
                display: none;
                background: white;
                border-radius: 16px;
                padding: 20px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.15);
                max-width: 350px;
                text-align: center;
                animation: slideUp 0.5s ease;
            }}
            
            @keyframes slideUp {{
                from {{
                    opacity: 0;
                    transform: translateY(20px);
                }}
                to {{
                    opacity: 1;
                    transform: translateY(0);
                }}
            }}
            
            .result-poster {{
                width: 150px;
                height: 225px;
                object-fit: cover;
                border-radius: 12px;
                margin-bottom: 15px;
                box-shadow: 0 5px 20px rgba(0,0,0,0.2);
            }}
            
            .result-title {{
                font-size: 20px;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 10px;
            }}
            
            .result-rating {{
                background: #f1c40f;
                color: #2c3e50;
                padding: 5px 15px;
                border-radius: 20px;
                font-weight: bold;
                display: inline-block;
                margin-bottom: 10px;
            }}
            
            .result-overview {{
                color: #7f8c8d;
                font-size: 14px;
                line-height: 1.5;
                max-height: 100px;
                overflow-y: auto;
            }}
            
            .confetti {{
                position: fixed;
                width: 10px;
                height: 10px;
                top: -10px;
                animation: fall 3s linear forwards;
            }}
            
            @keyframes fall {{
                to {{
                    transform: translateY(100vh) rotate(720deg);
                    opacity: 0;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="wheel-container">
            <div class="pointer"></div>
            <div class="wheel" id="{wheel_id}">
                <div class="wheel-inner">
                    {"".join([f'<div class="slice slice-{i}"></div>' for i in range(num_items)])}
                </div>
                <div class="center-circle">🎬</div>
            </div>
        </div>
        
        <button class="spin-btn" id="spinBtn" onclick="spinWheel()">
            🎰 ÇARKI ÇEVİR!
        </button>
        
        <div class="result-card" id="resultCard">
            <img class="result-poster" id="resultPoster" src="" alt="Poster">
            <div class="result-title" id="resultTitle"></div>
            <div class="result-rating" id="resultRating">⭐ 0.0</div>
            <p class="result-overview" id="resultOverview"></p>
        </div>
        
        <script>
            const items = {items_json};
            const numItems = {num_items};
            const sliceAngle = 360 / numItems;
            let isSpinning = false;
            let currentRotation = 0;
            
            function spinWheel() {{
                if (isSpinning) return;
                isSpinning = true;
                
                const wheel = document.getElementById('{wheel_id}');
                const spinBtn = document.getElementById('spinBtn');
                const resultCard = document.getElementById('resultCard');
                
                spinBtn.disabled = true;
                spinBtn.textContent = '🎰 Dönüyor...';
                resultCard.style.display = 'none';
                
                // Rastgele sonuç seç
                const winningIndex = Math.floor(Math.random() * numItems);
                
                // Dönüş açısını hesapla (5-8 tam tur + kazanan dilime)
                const spins = 5 + Math.random() * 3;
                const targetAngle = 360 - (winningIndex * sliceAngle + sliceAngle / 2);
                currentRotation += spins * 360 + targetAngle;
                
                wheel.style.transform = `rotate(${{currentRotation}}deg)`;
                
                // Animasyon bitince sonucu göster
                setTimeout(() => {{
                    const winner = items[winningIndex];
                    showResult(winner);
                    createConfetti();
                    
                    spinBtn.disabled = false;
                    spinBtn.textContent = '🎰 TEKRAR ÇEVİR!';
                    isSpinning = false;
                    
                    // Streamlit'e sonucu gönder
                    window.parent.postMessage({{
                        type: 'wheel_result',
                        data: winner
                    }}, '*');
                }}, 4500);
            }}
            
            function showResult(item) {{
                const resultCard = document.getElementById('resultCard');
                const poster = document.getElementById('resultPoster');
                const title = document.getElementById('resultTitle');
                const rating = document.getElementById('resultRating');
                const overview = document.getElementById('resultOverview');
                
                poster.src = item.poster_url || '[via.placeholder.com](https://via.placeholder.com/150x225?text=No+Poster)';
                title.textContent = item.title;
                rating.textContent = '⭐ ' + (item.vote_average || 0).toFixed(1);
                overview.textContent = item.overview || 'Açıklama bulunmuyor.';
                
                resultCard.style.display = 'block';
            }}
            
            function createConfetti() {{
                const colors = ['#e74c3c', '#3498db', '#2ecc71', '#f1c40f', '#9b59b6'];
                
                for (let i = 0; i < 50; i++) {{
                    setTimeout(() => {{
                        const confetti = document.createElement('div');
                        confetti.className = 'confetti';
                        confetti.style.left = Math.random() * 100 + '%';
                        confetti.style.background = colors[Math.floor(Math.random() * colors.length)];
                        confetti.style.animationDuration = (2 + Math.random() * 2) + 's';
                        document.body.appendChild(confetti);
                        
                        setTimeout(() => confetti.remove(), 3000);
                    }}, i * 30);
                }}
            }}
            
            // Sayfa yüklenince label'ları yerleştir
            document.addEventListener('DOMContentLoaded', () => {{
                const inner = document.querySelector('.wheel-inner');
                items.forEach((item, i) => {{
                    const label = document.createElement('div');
                    label.className = 'slice-label';
                    label.textContent = item.title.substring(0, 12);
                    label.style.transform = `rotate(${{i * sliceAngle + sliceAngle/2}}deg)`;
                    inner.appendChild(label);
                }});
            }});
        </script>
    </body>
    </html>
    """
    
    return html


def render_roulette_wheel(items: list[dict], height: int = 650) -> None:
    """
    Streamlit'te çark komponentini render et.
    
    Args:
        items: Çarkta gösterilecek içerikler
        height: Komponent yüksekliği
    """
    if not items:
        return
    
    wheel_html = create_wheel_html(items)
    components.html(wheel_html, height=height, scrolling=False)

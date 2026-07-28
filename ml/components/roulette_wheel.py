"""
Çark (Roulette) Komponenti
--------------------------
CSS/JS tabanlı interaktif dönen çark. Koyu (Netflix tarzı) tema.

Mimari notu: Kazanan artık JS tarafında rastgele seçilmiyor; Streamlit
(Python) tarafında seçiliyor ve `winning_index` ile komponente veriliyor.
Böylece JS -> Python `postMessage` köprüsüne ihtiyaç kalmıyor (bu köprü
eski sürümde hiç kurulmamıştı ve sonuç kartı asla görünmüyordu).
"""

import json
import streamlit as st
from typing import Optional


# Koyu temayla uyumlu, birbirinden ayırt edilebilir dilim renkleri
_SLICE_COLORS = [
    "#e50914", "#f5c518", "#3d5a80", "#7b2cbf",
    "#2a9d8f", "#e07a5f", "#4a4e69", "#e09f3e",
    "#c9184a", "#457b9d", "#6a994e", "#ee6c4d",
    "#9d4edd", "#118ab2", "#ffb703", "#8338ec",
]

_FALLBACK_POSTER = (
    "data:image/svg+xml;charset=UTF-8,"
    "%3Csvg xmlns='http://www.w3.org/2000/svg' width='150' height='225'%3E"
    "%3Crect width='150' height='225' fill='%231f1f1f'/%3E"
    "%3Ctext x='75' y='115' font-size='13' fill='%23666' text-anchor='middle' "
    "font-family='sans-serif'%3EPoster yok%3C/text%3E%3C/svg%3E"
)


def create_wheel_html(
    items: list[dict],
    wheel_id: str = "wheel",
    winning_index: Optional[int] = None,
    autoplay: bool = False,
    spin_seed: int = 0,
) -> str:
    """
    Dönen çark için HTML/CSS/JS oluştur.

    Args:
        items: Çarkta gösterilecek içerikler (max 20)
        wheel_id: Benzersiz çark ID'si
        winning_index: Kazanan olarak belirlenmiş dilimin indeksi (Python tarafından
            seçilir). None ise çark döner ama sabit bir sonuca kilitlenmez.
        autoplay: True ise komponent yüklendiğinde otomatik olarak döner.
        spin_seed: Her çevirmede değişen bir sayaç; component'in HTML içeriğini
            benzersiz kılıp Streamlit'in iframe'i yeniden yüklemesini garanti eder.

    Returns:
        HTML string
    """
    items = items[:20]
    num_items = len(items)

    if num_items == 0:
        return "<p style='color:#999;font-family:sans-serif;'>Gösterilecek içerik yok</p>"

    slice_angle = 360 / num_items
    slices_css = ""
    slices_data = []

    for i, item in enumerate(items):
        start_angle = i * slice_angle
        color = _SLICE_COLORS[i % len(_SLICE_COLORS)]

        slices_data.append({
            "title": item.get("title", "Bilinmiyor"),
            "id": item.get("id"),
            "poster_url": item.get("poster_url") or "",
            "overview": (item.get("overview") or "Açıklama yok.")[:200],
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

    items_json = json.dumps(slices_data, ensure_ascii=False)
    winning_index_js = "null" if winning_index is None else str(int(winning_index) % num_items)
    autoplay_js = "true" if autoplay else "false"

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

            html, body {{
                overflow: hidden;
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
                width: 420px;
                height: 420px;
                margin-bottom: 20px;
            }}

            .wheel {{
                width: 100%;
                height: 100%;
                border-radius: 50%;
                position: relative;
                overflow: hidden;
                box-shadow:
                    0 0 0 8px #2a2a2a,
                    0 0 0 12px #1a1a1a,
                    0 0 30px rgba(0,0,0,0.5);
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
                transform: translate(-50%, -50%);
                color: #ffffff;
                font-weight: 700;
                font-size: 11px;
                text-align: center;
                text-shadow: 0 1px 2px rgba(0,0,0,0.95), 0 0 5px rgba(0,0,0,0.8);
                white-space: nowrap;
                max-width: 68px;
                overflow: hidden;
                text-overflow: ellipsis;
                pointer-events: none;
            }}

            .center-circle {{
                position: absolute;
                width: 78px;
                height: 78px;
                background: linear-gradient(145deg, #e50914, #831010);
                border-radius: 50%;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                display: flex;
                align-items: center;
                justify-content: center;
                box-shadow: 0 4px 15px rgba(0,0,0,0.5);
                z-index: 10;
            }}

            .center-circle svg {{
                width: 32px;
                height: 32px;
                stroke: #fff;
                fill: none;
                stroke-width: 1.8;
            }}

            .pointer {{
                position: absolute;
                top: -15px;
                left: 50%;
                transform: translateX(-50%);
                width: 0;
                height: 0;
                border-left: 18px solid transparent;
                border-right: 18px solid transparent;
                border-top: 30px solid #e50914;
                filter: drop-shadow(0 3px 5px rgba(0,0,0,0.5));
                z-index: 20;
            }}

            .status-text {{
                color: #999;
                font-size: 13px;
                margin-bottom: 12px;
                min-height: 18px;
            }}

            .confetti {{
                position: fixed;
                width: 8px;
                height: 8px;
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
                <div class="center-circle">
                    <svg viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 9h18M3 15h18M8 4v16M16 4v16"/></svg>
                </div>
            </div>
        </div>

        <div class="status-text" id="statusText"></div>

        <script>
            const items = {items_json};
            const numItems = {num_items};
            const sliceAngle = 360 / numItems;
            const winningIndex = {winning_index_js};
            const autoplay = {autoplay_js};
            const spinSeed = {spin_seed};
            let currentRotation = 0;

            function spinToIndex(index) {{
                const wheel = document.getElementById('{wheel_id}');
                const statusText = document.getElementById('statusText');

                statusText.textContent = 'Dönüyor...';

                const spins = 5 + (spinSeed % 4);
                const targetAngle = 360 - (index * sliceAngle + sliceAngle / 2);
                currentRotation += spins * 360 + targetAngle;

                wheel.style.transform = `rotate(${{currentRotation}}deg)`;

                setTimeout(() => {{
                    createConfetti();
                    statusText.textContent = '🎉 Kazanan belirlendi!';
                }}, 4200);
            }}

            function createConfetti() {{
                const colors = ['#e50914', '#f5c518', '#7b2cbf', '#2a9d8f', '#e07a5f'];
                for (let i = 0; i < 40; i++) {{
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

            document.addEventListener('DOMContentLoaded', () => {{
                const inner = document.querySelector('.wheel-inner');
                const containerSize = inner.offsetWidth || 320;
                const center = containerSize / 2;
                const labelRadius = center * 0.62;

                items.forEach((item, i) => {{
                    const angleDeg = i * sliceAngle + sliceAngle / 2;
                    const angleRad = angleDeg * Math.PI / 180;
                    const x = center + labelRadius * Math.sin(angleRad);
                    const y = center - labelRadius * Math.cos(angleRad);

                    const fontSize = numItems > 16 ? 8 : numItems > 12 ? 9 : numItems > 8 ? 10 : 11;
                    const maxChars = numItems > 16 ? 6 : numItems > 12 ? 7 : numItems > 8 ? 8 : 10;

                    const label = document.createElement('div');
                    label.className = 'slice-label';
                    label.textContent = item.title.substring(0, maxChars);
                    label.style.left = x + 'px';
                    label.style.top = y + 'px';
                    label.style.fontSize = fontSize + 'px';
                    inner.appendChild(label);
                }});

                const statusText = document.getElementById('statusText');
                if (autoplay && winningIndex !== null) {{
                    spinToIndex(winningIndex);
                }} else {{
                    statusText.textContent = 'Çevirmek için yukarıdaki butona bas';
                }}
            }});
        </script>
    </body>
    </html>
    """

    return html


def render_roulette_wheel(
    items: list[dict],
    winning_index: Optional[int] = None,
    autoplay: bool = False,
    spin_seed: int = 0,
    height: int = 540,
) -> None:
    """
    Streamlit'te çark komponentini render et.

    Args:
        items: Çarkta gösterilecek içerikler
        winning_index: Python tarafından önceden seçilmiş kazanan indeksi
        autoplay: True ise komponent yüklenir yüklenmez döner
        spin_seed: Her çevirmede artan sayaç (iframe'in yeniden yüklenmesini garanti eder)
        height: Komponent yüksekliği
    """
    if not items:
        return

    wheel_html = create_wheel_html(
        items,
        winning_index=winning_index,
        autoplay=autoplay,
        spin_seed=spin_seed,
    )
    st.iframe(wheel_html, height=height)
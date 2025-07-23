document.addEventListener('DOMContentLoaded', () => {
    // 檢查函式庫
    if (typeof JsBarcode === 'undefined') {
        console.error("Fatal Error: JsBarcode library failed to load.");
        document.getElementById('message-area').textContent = "關鍵條碼函式庫載入失敗，請刷新頁面重試。";
        return;
    }
    
    // DOM 元素
    const playlistForm = document.getElementById('playlist-form');
    const playlistUrlInput = document.getElementById('playlist-url');
    const analyzeBtn = document.getElementById('analyze-btn');
    const analyzeBtnText = document.getElementById('analyze-btn-text');
    const messageArea = document.getElementById('message-area');
    const resultCard = document.getElementById('result-card');
    const playlistNameEl = document.getElementById('playlist-name');
    const moodDisplayEl = document.getElementById('mood-display');
    const discountDisplayEl = document.getElementById('discount-display');
    const generateBarcodeBtn = document.getElementById('generate-barcode-btn');
    const codeModal = document.getElementById('code-modal');
    const closeModalBtn = document.getElementById('close-modal-btn');
    
    // 應用程式狀態
    let currentAnalysisData = null;

    // [!!!] 最關鍵的設定點 [!!!]
    // 請將此處的網址，換成您在 Render 上為 "Spotify 專案" 部署的真實公開網址！
    const API_BASE_URL = "https://spotify-mood-service.onrender.com/"; // <--- 請務必修改這裡！
    
    playlistForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        // 禁用按鈕並顯示讀取狀態
        analyzeBtn.disabled = true;
        analyzeBtnText.textContent = '分析中...';
        messageArea.textContent = '';
        resultCard.style.display = 'none';

        try {
            const playlistUrl = playlistUrlInput.value;
            const response = await fetch(`${API_BASE_URL}/api/analyze-playlist`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ playlist_url: playlistUrl }),
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || '分析失敗，請檢查網址是否正確。');
            }
            
            currentAnalysisData = data;
            displayResults(data);

        } catch (error) {
            console.error('分析時發生錯誤:', error);
            messageArea.textContent = `錯誤：${error.message}`;
        } finally {
            // 重新啟用按鈕
            analyzeBtn.disabled = false;
            analyzeBtnText.textContent = '分析歌單心情';
        }
    });

    function displayResults(data) {
        playlistNameEl.textContent = data.playlist_name;
        moodDisplayEl.textContent = data.mood;
        
        const discountValue = (100 - data.discount_percentage) / 10;
        discountDisplayEl.textContent = `${discountValue.toFixed(1)} 折`;

        resultCard.style.display = 'block';
    }

    function showBarcode() {
        if (!currentAnalysisData) return;
        
        codeModal.classList.remove('hidden');
        
        const discountCode = `MILK-SPOTIFY-${currentAnalysisData.discount_percentage.toFixed(2)}-${Date.now()}`;
        
        JsBarcode("#barcode", discountCode, {
            format: "CODE128",
            lineColor: "#000",
            width: 2,
            height: 80,
            displayValue: true,
            fontSize: 18
        });
    }

    generateBarcodeBtn.addEventListener('click', showBarcode);
    closeModalBtn.addEventListener('click', () => {
        codeModal.classList.add('hidden');
    });
});

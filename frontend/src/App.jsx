import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Upload, FileArchive, CheckCircle2, AlertCircle, XCircle, ChevronDown, ChevronRight, Activity, Cpu, Download, MessageSquare, Send, BookOpen, Sun, Moon, Edit2, FileCode, Code2, ShieldCheck, Search, Palette, Box, ShieldAlert } from 'lucide-react';

function ChatInputBox({ onSend, loading }) {
  const [input, setInput] = useState('');

  const handleSend = () => {
    if (!input.trim() || loading) return;
    onSend(input);
    setInput('');
  };

  return (
    <div className="p-4 bg-transparent z-10 m-4 relative border border-slate-200 dark:border-slate-800 rounded-2xl bg-white dark:bg-slate-900 shadow-sm flex items-end mb-6">
      <textarea 
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={(e) => {
            if(e.key === 'Enter' && !e.shiftKey) { 
                e.preventDefault(); 
                handleSend(); 
            }
        }}
        placeholder="e-İrsaliye'de karekod zorunlu mu? Hangi UBL elementine yazılır?"
        className="flex-1 outline-none resize-none pt-4 pb-4 px-4 text-sm font-medium bg-transparent dark:text-white min-h-[56px] max-h-[200px]"
        rows={1}
      />
      <button 
        onClick={handleSend}
        disabled={loading || !input.trim()}
        className={`p-3 m-2 rounded-xl flex items-center justify-center transition-all ${
          loading || !input.trim() ? 'bg-slate-100 dark:bg-slate-800 text-slate-400 cursor-not-allowed' : 'bg-indigo-600 text-white hover:bg-indigo-700 shadow-md shadow-indigo-600/30'
        }`}>
        <Send className="w-5 h-5" />
      </button>
    </div>
  );
}

function App() {
  const [oldFile, setOldFile] = useState(null);
  const [newFile, setNewFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);

  const [schXmlFile, setSchXmlFile] = useState(null);
  const [schSchFile, setSchSchFile] = useState(null);
  const [schLoading, setSchLoading] = useState(false);
  const [schResults, setSchResults] = useState(null);
  const [schError, setSchError] = useState(null);

  const [sanFile, setSanFile] = useState(null);
  const [sanLoading, setSanLoading] = useState(false);
  const [sanResult, setSanResult] = useState(null);
  const [sanError, setSanError] = useState(null);

  // Röntgen (X-Ray) States
  const [xrayFile, setXrayFile] = useState(null);
  const [xrayFileLoading, setXrayFileLoading] = useState(false);
  const [xrayResult, setXrayResult] = useState(null);
  const [xrayError, setXrayError] = useState(null);
  const [xrayResults, setXrayResults] = useState(null);
  const [xrayLoading, setXrayLoading] = useState(false);
  const [xraySelectedText, setXraySelectedText] = useState("");
  const [copiedIndex, setCopiedIndex] = useState(null);
  const [highlightedLine, setHighlightedLine] = useState(null);
  const [xmlText, setXmlText] = useState("");
  const [leftWidth, setLeftWidth] = useState(50); // Balanced 50/50 split by default!
  const [isDragging, setIsDragging] = useState(false);
  const containerRef = useRef(null);

  const startResizing = (mouseDownEvent) => {
    setIsDragging(true);
    mouseDownEvent.preventDefault();
  };

  useEffect(() => {
    if (!isDragging) return;

    const handleMouseMove = (e) => {
      if (!containerRef.current) return;
      const containerRect = containerRef.current.getBoundingClientRect();
      const relativeX = e.clientX - containerRect.left;
      let percentage = (relativeX / containerRect.width) * 100;
      
      // Boundaries: min 30%, max 70%
      if (percentage < 30) percentage = 30;
      if (percentage > 70) percentage = 70;
      
      setLeftWidth(percentage);
    };

    const handleMouseUp = () => {
      setIsDragging(false);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging]);

  useEffect(() => {
    if (xrayResult && xrayResult.xml_base64) {
      try {
        const binaryString = atob(xrayResult.xml_base64);
        const bytes = new Uint8Array(binaryString.length);
        for (let i = 0; i < binaryString.length; i++) {
          bytes[i] = binaryString.charCodeAt(i);
        }
        const decoded = new TextDecoder('utf-8').decode(bytes);
        setXmlText(decoded);
        setHighlightedLine(null);
      } catch (err) {
        console.error("Error decoding XML base64", err);
        try {
          setXmlText(atob(xrayResult.xml_base64));
        } catch (e) {
          setXmlText("");
        }
        setHighlightedLine(null);
      }
    } else {
      setXmlText("");
      setHighlightedLine(null);
    }
  }, [xrayResult]);

  const findXPathInXml = async (searchText, targetXmlBase64) => {
      if (!targetXmlBase64) return;
      setXrayLoading(true);
      setXraySelectedText(searchText);
      
      const formData = new FormData();
      formData.append('xml_base64', targetXmlBase64);
      formData.append('search_text', searchText);
      
      try {
          const response = await axios.post('http://localhost:8000/api/xray', formData);
          if (response.data.status === 'success') {
              const matchedResults = response.data.data;
              setXrayResults(matchedResults);
              
              if (matchedResults && matchedResults.length > 0) {
                  const targetLine = matchedResults[0].line;
                  setHighlightedLine(targetLine);
                  setTimeout(() => {
                      const lineElem = document.getElementById(`xml-line-${targetLine}`);
                      if (lineElem) {
                          lineElem.scrollIntoView({ behavior: 'smooth', block: 'center' });
                      }
                  }, 100);
              }
          } else {
              setXrayResults([]);
          }
      } catch (err) {
          console.error("X-Ray Error", err);
          setXrayResults([]);
      } finally {
          setXrayLoading(false);
      }
  };

  const handleIframeLoad = (e, targetXmlBase64) => {
    const iframe = e.target;
    if (iframe.contentWindow) {
       iframe.contentWindow.document.addEventListener('mouseup', () => {
          const selection = iframe.contentWindow.getSelection();
          if (selection && selection.toString().trim()) {
             const selectedText = selection.toString().trim();
             if (selectedText.length > 0 && selectedText.length < 200) {
                 findXPathInXml(selectedText, targetXmlBase64);
             }
          }
       });
    }
  };

  const handleXrayFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      setXrayFile(e.target.files[0]);
      setXrayResult(null);
      setXrayError(null);
      setXrayResults(null);
      setXraySelectedText("");
    }
  };

  const handleXrayUpload = async (file) => {
    const targetFile = file || xrayFile;
    if (!targetFile) {
      setXrayError("Lütfen bir XML dosyası yükleyiniz.");
      return;
    }
    setXrayFileLoading(true);
    setXrayError(null);
    setXrayResult(null);
    setXrayResults(null);
    setXraySelectedText("");
    const formData = new FormData();
    formData.append('file', targetFile);

    try {
      const response = await axios.post('http://localhost:8000/api/render', formData);
      setXrayResult(response.data.data);
    } catch (err) {
      setXrayError(err.response?.data?.detail || "Sunucu ile iletişim hatası veya fatura görselleştirme sorunu.");
    } finally {
      setXrayFileLoading(false);
    }
  };

  const [activeTab, setActiveTab] = useState('diff'); // 'diff', 'scenarios' or 'chat'
  const [activeMainTab, setActiveMainTab] = useState('analyzer');
  const [collapsedFiles, setCollapsedFiles] = useState({});
  const [chatMessages, setChatMessages] = useState([{role: 'bot', text: 'Merhaba! GİB kılavuzları ve e-Dönüşüm kuralları hakkında bana her şeyi sorabilirsin.'}]);
  const [chatLoading, setChatLoading] = useState(false);
  const messagesEndRef = useRef(null);

  // Reconciliation (DB Auditor) States & Handlers
  const [reconConfig, setReconConfig] = useState({
    server: 'localhost\\SQLOTOMASYON',
    company_code: '',
    year: '',
    username: '',
    password: '',
    trusted: true
  });
  const [reconFile, setReconFile] = useState(null);
  const [reconResults, setReconResults] = useState(null);
  const [reconLoading, setReconLoading] = useState(false);
  const [reconError, setReconError] = useState(null);

  const [reconCompanies, setReconCompanies] = useState([]);
  const [reconYears, setReconYears] = useState([]);
  const [reconDbLoading, setReconDbLoading] = useState(false);

  const handleFetchCompanies = async () => {
    setReconDbLoading(true);
    setReconError(null);
    const formData = new FormData();
    formData.append("server", reconConfig.server);
    formData.append("trusted", reconConfig.trusted ? "true" : "false");
    if (reconConfig.username) formData.append("username", reconConfig.username);
    if (reconConfig.password) formData.append("password", reconConfig.password);

    try {
      const response = await axios.post("http://localhost:8000/api/reconcile/companies", formData);
      setReconCompanies(response.data);
      if (response.data.length > 0) {
        const firstComp = response.data[0];
        setReconConfig(prev => ({ ...prev, company_code: firstComp }));
        await handleFetchYears(firstComp);
      }
    } catch (err) {
      setReconError(err.response?.data?.detail || "Veritabanından firmalar listelenirken bir hata oluştu.");
    } finally {
      setReconDbLoading(false);
    }
  };

  const handleFetchYears = async (companyCode) => {
    const formData = new FormData();
    formData.append("server", reconConfig.server);
    formData.append("company_code", companyCode);
    formData.append("trusted", reconConfig.trusted ? "true" : "false");
    if (reconConfig.username) formData.append("username", reconConfig.username);
    if (reconConfig.password) formData.append("password", reconConfig.password);

    try {
      const response = await axios.post("http://localhost:8000/api/reconcile/years", formData);
      setReconYears(response.data);
      if (response.data.length > 0) {
        setReconConfig(prev => ({ ...prev, year: response.data[0] }));
      } else {
        setReconConfig(prev => ({ ...prev, year: "" }));
      }
    } catch (err) {
      setReconError(err.response?.data?.detail || "Firmaya ait çalışma yılları yüklenirken hata oluştu.");
    }
  };


  const handleReconcileSubmit = async (e) => {
    e.preventDefault();
    if (!reconFile) {
      setReconError("Lütfen karşılaştırma için bir UBL XML dosyası yükleyin.");
      return;
    }
    
    setReconLoading(true);
    setReconError(null);
    setReconResults(null);
    
    const formData = new FormData();
    formData.append("file", reconFile);
    formData.append("server", reconConfig.server);
    formData.append("company_code", reconConfig.company_code);
    formData.append("year", reconConfig.year);
    formData.append("trusted", reconConfig.trusted ? "true" : "false");
    if (reconConfig.username) formData.append("username", reconConfig.username);
    if (reconConfig.password) formData.append("password", reconConfig.password);
    
    try {
      const response = await axios.post("http://localhost:8000/api/reconcile", formData, {
        headers: {
          "Content-Type": "multipart/form-data"
        }
      });
      if (response.data && response.data.status === "error") {
        setReconError(response.data.message || "Mutabakat sırasında bir hata oluştu.");
        setReconResults(null);
      } else {
        setReconResults(response.data);
      }
    } catch (err) {
      setReconError(err.response?.data?.detail || "Veritabanı mutabakatı sırasında bir sunucu hatası oluştu.");
    } finally {
      setReconLoading(false);
    }
  };

  
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages, chatLoading]);

  const [pdfUploadLoading, setPdfUploadLoading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [learningProgress, setLearningProgress] = useState(0);
  const [pdfFile, setPdfFile] = useState(null);
  
  const [modalConfig, setModalConfig] = useState({
    isOpen: false,
    type: 'success', // 'success' or 'error'
    title: '',
    message: ''
  });

  const showPremiumModal = (type, title, message) => {
    setModalConfig({
      isOpen: true,
      type,
      title,
      message
    });
  };

  const [diffModal, setDiffModal] = useState({
    isOpen: false,
    fileName: '',
    diffLines: [],
    loading: false,
    error: '',
    showOnlyChanges: true
  });

  const handleViewCodeDiff = async (filePath) => {
    setDiffModal(prev => ({ ...prev, isOpen: true, fileName: filePath, diffLines: [], loading: true, error: '' }));
    try {
      const response = await axios.get(`http://localhost:8000/api/diff/file?file_path=${encodeURIComponent(filePath)}`);
      setDiffModal(prev => ({
        ...prev,
        loading: false,
        diffLines: response.data.diff
      }));
    } catch (err) {
      setDiffModal(prev => ({
        ...prev,
        loading: false,
        error: err.response?.data?.detail || 'Kod farkı yüklenirken bir hata oluştu.'
      }));
    }
  };

  const [geminiKey, setGeminiKey] = useState('');

  const [keyLoading, setKeyLoading] = useState(false);
  const [isApiKeySaved, setIsApiKeySaved] = useState(false);
  const [darkMode, setDarkMode] = useState(false);

  // Schematron Saved Rules States
  const [savedSchematrons, setSavedSchematrons] = useState([]);
  const [selectedSchFilename, setSelectedSchFilename] = useState("");

  const fetchSavedSchematrons = () => {
     axios.get('http://localhost:8000/api/schematron/list')
      .then(res => {
          const files = res.data.data;
          setSavedSchematrons(files);
          if (files.length > 0) {
              setSelectedSchFilename(files[0]);
          }
      })
      .catch(console.error);
  };

  useEffect(() => {
    axios.get('http://localhost:8000/api/settings/apikey/status')
      .then(res => setIsApiKeySaved(res.data.hasKey))
      .catch(err => console.error(err));
      
    // if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
    //    setDarkMode(true);
    // }
    
    fetchSavedSchematrons();
  }, []);

  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [darkMode]);
  const handleFileChange = (e, type) => {
    if (e.target.files && e.target.files.length > 0) {
      if (type === 'old') setOldFile(e.target.files[0]);
      if (type === 'new') setNewFile(e.target.files[0]);
    }
  };

  const handleSchFileChange = (e, type) => {
    if (e.target.files && e.target.files.length > 0) {
      if (type === 'xml') setSchXmlFile(e.target.files[0]);
      if (type === 'sch') setSchSchFile(e.target.files[0]);
    }
  };

  const handleSanFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      setSanFile(e.target.files[0]);
    }
  };

  const handleAnalyze = async () => {
    if (!oldFile || !newFile) {
      setError("Lütfen her iki (eski ve yeni) ZIP paketini de yükleyiniz.");
      return;
    }

    setLoading(true);
    setError(null);
    setResults(null);
    setCollapsedFiles({});

    const formData = new FormData();
    formData.append('old_package', oldFile);
    formData.append('new_package', newFile);

    try {
      const response = await axios.post('http://localhost:8000/api/analyze', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setResults(response.data.data);
    } catch (err) {
      setError(err.response?.data?.detail || "Sunucu ile iletişim kurulamadı veya bir hata oluştu.");
    } finally {
      setLoading(false);
    }
  };

  const handleUploadSchematron = async () => {
    if (!schSchFile) return;
    const formData = new FormData();
    formData.append('file', schSchFile);
    try {
        await axios.post('http://localhost:8000/api/schematron/upload', formData);
        fetchSavedSchematrons();
        setSelectedSchFilename(schSchFile.name);
        setSchSchFile(null);
        showPremiumModal('success', 'Şematron Kaydedildi', 'Özel doğrulama şematron kuralı sunucuya başarıyla yüklendi!');
    } catch(err) {
        showPremiumModal('error', 'Yükleme Başarısız', 'Şematron dosyası yüklenirken bir hata oluştu: ' + err.message);
    }
  };

  const handleSchematronValidate = async () => {
    if (!schXmlFile) {
      setSchError("Lütfen bir XML dosyasını yükleyiniz.");
      return;
    }
    if (!schSchFile && !selectedSchFilename) {
        setSchError("Lütfen bir .sch dosyasını yükleyin veya sistemden seçin.");
        return;
    }
    setSchLoading(true);
    setSchError(null);
    setSchResults(null);
    const formData = new FormData();
    formData.append('xml_file', schXmlFile);
    if (schSchFile) {
        formData.append('sch_file', schSchFile);
    }
    if (selectedSchFilename) {
        formData.append('sch_filename', selectedSchFilename);
    }

    try {
      const response = await axios.post('http://localhost:8000/api/validate/schematron', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setSchResults(response.data.data);
    } catch (err) {
      setSchError(err.response?.data?.detail || "Sunucu ile iletişim sağlandığında hata oluştu.");
    } finally {
      setSchLoading(false);
    }
  };

  const handleSanitize = async () => {
    if (!sanFile) {
      setSanError("Lütfen maskelenecek XML dosyasını yükleyiniz.");
      return;
    }
    setSanLoading(true);
    setSanError(null);
    setSanResult(null);
    const formData = new FormData();
    formData.append('file', sanFile);

    try {
      const response = await axios.post('http://localhost:8000/api/sanitize/xml', formData);
      setSanResult(response.data.data);
    } catch (err) {
      setSanError(err.response?.data?.detail || "Sunucu ile iletişim hatası veya maskeleme sorunu.");
    } finally {
      setSanLoading(false);
    }
  };

  const downloadSanitizedXml = () => {
      if (!sanResult || !sanResult.xml_base64) return;
      const byteCharacters = atob(sanResult.xml_base64);
      const byteNumbers = new Array(byteCharacters.length);
      for (let i = 0; i < byteCharacters.length; i++) {
          byteNumbers[i] = byteCharacters.charCodeAt(i);
      }
      const byteArray = new Uint8Array(byteNumbers);
      const blob = new Blob([byteArray], {type: 'application/xml'});
      
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', sanResult.filename || 'Maskelenmis_Belge.xml');
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
  };

  const handlePdfChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      setPdfFile(e.target.files[0]);
    }
  };

  const handleIngestPdf = async () => {
    if (!pdfFile) return;
    setPdfUploadLoading(true);
    setUploadProgress(0);
    setLearningProgress(1); // Start at 1% immediately to give instant visual feedback

    const formData = new FormData();
    formData.append('file', pdfFile);

    // Dynamic interval that increases smoothly and caps at 98%
    let currentProgress = 1;
    const progressInterval = setInterval(() => {
      if (currentProgress < 30) {
        currentProgress += Math.random() * 5 + 3; // Fast at first (+3-8%)
      } else if (currentProgress < 70) {
        currentProgress += Math.random() * 3 + 1; // Moderate (+1-4%)
      } else if (currentProgress < 95) {
        currentProgress += Math.random() * 1.5 + 0.5; // Slower (+0.5-2%)
      } else if (currentProgress < 98) {
        currentProgress += 0.2; // Crawl near the limit
      }
      
      if (currentProgress > 98) currentProgress = 98;
      setLearningProgress(Math.floor(currentProgress));
    }, 450);

    try {
      const resp = await axios.post('http://localhost:8000/api/rag/ingest', formData, {
        onUploadProgress: (progressEvent) => {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          setUploadProgress(percentCompleted);
        }
      });

      clearInterval(progressInterval);
      setLearningProgress(100);

      // Delay slightly to let the user see 100% completion
      setTimeout(() => {
        setPdfFile(null);
        setPdfUploadLoading(false);
        setUploadProgress(0);
        setLearningProgress(0);
        showPremiumModal('success', 'Eğitim Tamamlandı', resp.data.message);
      }, 500);

    } catch (err) {
      clearInterval(progressInterval);
      setPdfUploadLoading(false);
      setUploadProgress(0);
      setLearningProgress(0);
      showPremiumModal('error', 'Hata Oluştu', err.response?.data?.detail || "Kılavuz yüklenirken veya eğitilirken bir hata oluştu. Lütfen bağlantınızı ve API Key bilginizi kontrol edin.");
    }
  };

  const handleSendChat = async (userMsg) => {
    if (!userMsg.trim()) return;
    
    setChatMessages(prev => [...prev, {role: 'user', text: userMsg}]);
    setChatLoading(true);
    
    const formData = new FormData();
    formData.append('query', userMsg);
    
    try {
      const resp = await axios.post('http://localhost:8000/api/rag/chat', formData);
      const answer = resp.data.data.answer;
      setChatMessages(prev => [...prev, {role: 'bot', text: answer}]);
    } catch (err) {
      console.error(err);
      setChatMessages(prev => [...prev, {role: 'bot', text: "Hata: Sunucuya bağlanılamadı veya hatalı API Key. Lütfen backend .env dosyanızı kontrol ediniz."}]);
    } finally {
      setChatLoading(false);
    }
  };

  const handleSendChatStream = async (userMsg) => {
    if (!userMsg.trim()) return;
    
    setChatMessages(prev => [...prev, {role: 'user', text: userMsg}]);
    setChatLoading(true);
    
    // Geçici olarak boş bot mesajı ekle
    setChatMessages(prev => [...prev, {role: 'bot', text: ''}]);
    
    const formData = new FormData();
    formData.append('query', userMsg);
    
    try {
      const response = await fetch('http://localhost:8000/api/rag/chat/stream', {
        method: 'POST',
        body: formData,
      });
      
      if (!response.ok) {
        throw new Error(`HTTP hatası! status: ${response.status}`);
      }
      
      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      
      setChatLoading(false);

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        
        const chunk = decoder.decode(value, { stream: true });
        
        setChatMessages(prev => {
          const newMessages = [...prev];
          const lastIndex = newMessages.length - 1;
          newMessages[lastIndex] = {
            ...newMessages[lastIndex],
            text: newMessages[lastIndex].text + chunk
          };
          return newMessages;
        });
      }
    } catch (err) {
      console.error(err);
      setChatMessages(prev => {
        const newMessages = [...prev];
        const lastIndex = newMessages.length - 1;
        newMessages[lastIndex] = {
            ...newMessages[lastIndex],
            text: "Hata: Sunucuya bağlanılamadı veya yayın akışı başlatılamadı."
        };
        return newMessages;
      });
      setChatLoading(false);
    }
  };


  const handleSaveApiKey = async () => {
    if (!geminiKey.trim()) return;
    setKeyLoading(true);
    const formData = new FormData();
    formData.append('key', geminiKey.trim());
    try {
      const resp = await axios.post('http://localhost:8000/api/settings/apikey', formData);
      setIsApiKeySaved(true);
      setGeminiKey('');
      showPremiumModal('success', 'API Anahtarı Aktif', resp.data.message);
    } catch (err) {
      showPremiumModal('error', 'API Anahtarı Kaydedilemedi', err.response?.data?.detail || "API Anahtarı kaydedilirken bir sunucu hatası oluştu.");
    } finally {
      setKeyLoading(false);
    }
  };

  const exportScenariosToCSV = () => {
    if (!results || !results.scenarios) return;
    
    // Create CSV content (Semicolon ; is preferred for Turkish Excel compatibility)
    const headers = ['Hedef (XSD/Element)', 'Dosya', 'Degisim Tipi', 'Pozitif Senaryo', 'Negatif Senaryo'];
    const csvRows = [headers.join(';')];
    
    results.scenarios.forEach(scen => {
      const row = [
        `"${scen.target.replace(/"/g, '""')}"`,
        `"${scen.file.replace(/"/g, '""')}"`,
        `"${scen.type.replace(/"/g, '""')}"`,
        `"${scen.positive.replace(/"/g, '""')}"`,
        `"${scen.negative.replace(/"/g, '""')}"`
      ];
      csvRows.push(row.join(';'));
    });
    
    // Add BOM for UTF-8 Excel compatibility
    const csvString = '\uFEFF' + csvRows.join('\n');
    const blob = new Blob([csvString], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', 'GIB_Test_Senaryolari.csv');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-800 dark:text-slate-200 font-sans">
      {/* HEADER */}
      <header className="bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 px-8 py-4 flex items-center justify-between sticky top-0 z-10 shadow-sm transition-colors duration-200">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-white rounded-lg flex items-center justify-center border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
            <img src="/gib_logo.png" alt="GİB Logo" className="w-8 h-8 object-contain" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-900 dark:text-slate-100 tracking-tight">GİB Paket Analizörü</h1>
            <p className="text-xs text-slate-500 dark:text-slate-400">Görkem Gönen Hedef Projesi</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <button 
            onClick={() => setDarkMode(!darkMode)}
            className="p-2 rounded-full hover:bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 transition-colors"
            title="Temayı Değiştir">
            {darkMode ? <Sun className="w-5 h-5"/> : <Moon className="w-5 h-5"/>}
          </button>
          <div className="text-sm font-medium bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 px-3 py-1.5 rounded-full flex items-center gap-2">
            <Cpu className="w-4 h-4 text-indigo-500" /> Yapay Zeka & Kural Destekli
          </div>
        </div>
      </header>

      {/* MAIN NAV TABS */}
      <div className="bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800">
        <div className="max-w-6xl mx-auto px-4 flex">
          <button 
            onClick={() => setActiveMainTab('analyzer')} 
            className={`py-4 px-6 font-bold text-sm border-b-2 transition flex items-center gap-2 ${activeMainTab === 'analyzer' ? 'border-indigo-600 text-indigo-700 bg-indigo-50/50' : 'border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:text-slate-200 hover:bg-slate-50 dark:bg-slate-950'}`}>
            📦 GİB Paket Analizörü
          </button>
          <button 
            onClick={() => setActiveMainTab('schematron')} 
            className={`py-4 px-6 font-bold text-sm border-b-2 transition flex items-center gap-2 ${activeMainTab === 'schematron' ? 'border-emerald-600 text-emerald-700 bg-emerald-50/50' : 'border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:text-slate-200 hover:bg-slate-50 dark:bg-slate-950'}`}>
            <CheckCircle2 className="w-5 h-5"/> Şematron Doğrulama
          </button>
          <button 
            onClick={() => setActiveMainTab('sanitizer')} 
            className={`py-4 px-6 font-bold text-sm border-b-2 transition flex items-center gap-2 ${activeMainTab === 'sanitizer' ? 'border-amber-600 text-amber-700 bg-amber-50/50' : 'border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:text-slate-200 hover:bg-slate-50 dark:bg-slate-950'}`}>
            <ShieldCheck className="w-5 h-5"/> XSLT İşlemleri
          </button>
          <button 
            onClick={() => {
              setActiveMainTab('xray');
              setXrayResults(null);
              setXraySelectedText("");
            }} 
            className={`py-4 px-6 font-bold text-sm border-b-2 transition flex items-center gap-2 ${activeMainTab === 'xray' ? 'border-violet-600 text-violet-700 bg-violet-50/50' : 'border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:text-slate-200 hover:bg-slate-50 dark:bg-slate-950'}`}>
            <Search className="w-5 h-5"/> Fatura Röntgeni
          </button>
          <button 
            onClick={() => setActiveMainTab('assistant')} 
            className={`py-4 px-6 font-bold text-sm border-b-2 transition flex items-center gap-2 ${activeMainTab === 'assistant' ? 'border-blue-600 text-blue-700 bg-blue-50/50' : 'border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:text-slate-200 hover:bg-slate-50 dark:bg-slate-950'}`}>
            <MessageSquare className="w-5 h-5"/> Akıllı GİB Asistanı
          </button>
          <button 
            onClick={() => setActiveMainTab('reconciliation')} 
            className={`py-4 px-6 font-bold text-sm border-b-2 transition flex items-center gap-2 ${activeMainTab === 'reconciliation' ? 'border-rose-600 text-rose-700 bg-rose-50/50 animate-fadeIn' : 'border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:text-slate-200 hover:bg-slate-50 dark:bg-slate-950'}`}>
            <Activity className="w-5 h-5 text-rose-500"/> Veritabanı Mutabakatı
          </button>
        </div>
      </div>

      <main className={`w-full py-8 transition-all duration-300 ${
        activeMainTab === 'xray' && xrayResult 
        ? 'max-w-[1920px] px-8' 
        : 'max-w-6xl px-4'
      } mx-auto`}>
        
        {/* ANALYZER TAB */}
        <div className={activeMainTab === 'analyzer' ? 'block' : 'hidden'}>
        {/* UPLOAD SECTION */}
        {!results && (
          <div className="bg-white dark:bg-slate-900 rounded-2xl p-8 shadow-sm border border-slate-200 dark:border-slate-800 mb-8 max-w-4xl mx-auto">
            <div className="text-center mb-10">
              <h2 className="text-2xl font-bold mb-2">Karşılaştırma Paketlerini Yükleyin</h2>
              <p className="text-slate-500 dark:text-slate-400">Gelir İdaresi Başkanlığı tarafından yayınlanan eski ve yeni versiyon XSD/XSLT paketlerini ZIP olarak sisteme yükleyin.</p>
            </div>

            <div className="flex gap-6 mb-8">
              <div className="flex-1">
                <label className="block text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">Mevcut (Eski) Paket (.zip)</label>
                <div className="relative border-2 border-dashed border-slate-300 dark:border-slate-700 rounded-xl p-8 text-center hover:bg-slate-50 dark:bg-slate-950 hover:border-indigo-400 transition-colors cursor-pointer" onClick={() => document.getElementById('old-file').click()}>
                  <input id="old-file" type="file" accept=".zip" className="hidden" onChange={(e) => handleFileChange(e, 'old')} />
                  <FileArchive className={`w-12 h-12 mx-auto mb-3 ${oldFile ? 'text-indigo-600' : 'text-slate-400'}`} />
                  {oldFile ? (
                    <div>
                      <p className="font-semibold text-indigo-700">{oldFile.name}</p>
                      <p className="text-xs text-slate-500 dark:text-slate-400">{(oldFile.size / 1024 / 1024).toFixed(2)} MB</p>
                    </div>
                  ) : (
                    <p className="text-slate-500 dark:text-slate-400 text-sm">Eski paket sürümünü seçmek için tıklayın.</p>
                  )}
                </div>
              </div>

              <div className="flex-1">
                <label className="block text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">Güncel (Yeni) Paket (.zip)</label>
                <div className="relative border-2 border-dashed border-slate-300 dark:border-slate-700 rounded-xl p-8 text-center hover:bg-slate-50 dark:bg-slate-950 hover:border-indigo-400 transition-colors cursor-pointer" onClick={() => document.getElementById('new-file').click()}>
                  <input id="new-file" type="file" accept=".zip" className="hidden" onChange={(e) => handleFileChange(e, 'new')} />
                  <FileArchive className={`w-12 h-12 mx-auto mb-3 ${newFile ? 'text-indigo-600' : 'text-slate-400'}`} />
                  {newFile ? (
                    <div>
                      <p className="font-semibold text-indigo-700">{newFile.name}</p>
                      <p className="text-xs text-slate-500 dark:text-slate-400">{(newFile.size / 1024 / 1024).toFixed(2)} MB</p>
                    </div>
                  ) : (
                    <p className="text-slate-500 dark:text-slate-400 text-sm">Yeni paket sürümünü seçmek için tıklayın.</p>
                  )}
                </div>
              </div>
            </div>

            {error && (
              <div className="bg-red-50 text-red-600 p-4 rounded-lg flex items-center gap-3 mb-6">
                 <AlertCircle className="w-5 h-5" /> {error}
              </div>
            )}

            <button 
              onClick={handleAnalyze} 
              disabled={loading || !oldFile || !newFile}
              className={`w-full py-4 rounded-xl flex items-center justify-center gap-2 font-bold text-lg transition-all ${
                loading || !oldFile || !newFile 
                ? 'bg-slate-100 dark:bg-slate-800 text-slate-400 cursor-not-allowed' 
                : 'bg-indigo-600 text-white hover:bg-indigo-700 hover:shadow-lg shadow-indigo-600/30'
              }`}
            >
              {loading ? (
                <>
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-current" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                  Paketler Analiz Ediliyor...
                </>
              ) : (
                <><Upload className="w-5 h-5"/> Farkları Analiz Et ve Senaryo Üret</>
              )}
            </button>
          </div>
        )}

        {/* RESULTS SECTION */}
        {results && (
          <div className="space-y-6">
            
            <div className="bg-white dark:bg-slate-900 rounded-2xl p-6 shadow-sm border border-slate-200 dark:border-slate-800 flex justify-between items-center">
               <div>
                  <h2 className="text-xl font-bold">Analiz Sonucu Özeti</h2>
                  <p className="text-slate-500 dark:text-slate-400 text-sm mt-1">Eski pakette {results.old_files_found}, yeni pakette {results.new_files_found} dosya analiz edildi.</p>
               </div>
               <button onClick={() => setResults(null)} className="text-sm font-semibold text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:text-slate-200">
                 Yeni Paket Yükle
               </button>
            </div>

            {/* TAB MENU */}
            <div className="flex justify-between items-end border-b border-slate-200 dark:border-slate-800">
               <div className="flex space-x-2">
                 <button 
                   onClick={() => setActiveTab('diff')} 
                   className={`px-6 py-3 font-semibold text-sm rounded-t-lg transition border-b-2 ${activeTab === 'diff' ? 'bg-white dark:bg-slate-900 border-indigo-600 text-indigo-700' : 'border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:text-slate-200 hover:bg-slate-50 dark:bg-slate-950'}`}>
                   Fark Görüntüleyici (Diff)
                 </button>
                 <button 
                   onClick={() => setActiveTab('scenarios')}
                   className={`px-6 py-3 font-semibold text-sm rounded-t-lg transition border-b-2 flex items-center gap-2 ${activeTab === 'scenarios' ? 'bg-white dark:bg-slate-900 border-emerald-500 text-emerald-700' : 'border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:text-slate-200 hover:bg-slate-50 dark:bg-slate-950'}`}>
                   Otomatik Test Senaryoları
                   <span className="bg-emerald-100 text-emerald-700 py-0.5 px-2 rounded-full text-xs font-bold">{results.scenarios.length} Senaryo</span>
                 </button>
                 {/* Assistant moved to main tabs */}
               </div>
               
               {activeTab === 'diff' && (
                 <button 
                   onClick={() => {
                        const newCollapsed = {};
                        results.diff_results.forEach(f => newCollapsed[f.file] = true);
                        setCollapsedFiles(newCollapsed);
                   }} 
                   className="mb-2 mr-4 px-4 py-2 bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 text-xs font-semibold rounded-lg hover:bg-slate-200 dark:hover:bg-slate-700 transition shadow-sm">
                   Tüm Dosyaları Gizle
                 </button>
               )}
               
               {activeTab === 'scenarios' && (
                 <button 
                   onClick={exportScenariosToCSV} 
                   className="mb-2 mr-4 px-4 py-2 bg-slate-800 text-white text-sm font-semibold rounded-lg hover:bg-slate-900 transition flex items-center gap-2 shadow-sm">
                   <Download className="w-4 h-4" /> Senaryoları İndir (CSV/Excel)
                 </button>
               )}
            </div>

            {/* CONTENT TABS */}
            <div className="bg-white dark:bg-slate-900 rounded-2xl rounded-tl-none shadow-sm border border-slate-200 dark:border-slate-800 overflow-hidden">
               {activeTab === 'diff' && (
                 <div className="p-6">
                    {results.diff_results.filter(f => f.status !== 'unchanged').length === 0 ? (
                      <div className="text-center py-20 text-slate-500 dark:text-slate-400">
                         <CheckCircle2 className="w-16 h-16 mx-auto mb-4 text-slate-300" />
                         <p className="text-lg font-medium">Paketler arasında herhangi bir farklılık bulunamadı.</p>
                      </div>
                    ) : (
                      <div className="space-y-6">
                         {results.diff_results.filter(f => f.status !== 'unchanged').map((file, idx) => {
                            const defaultCollapsed = file.file.includes('general.xslt') || file.diff.length > 50;
                            const isCollapsed = collapsedFiles[file.file] !== undefined ? collapsedFiles[file.file] : defaultCollapsed;
                            
                            return (
                               <div key={idx} className="border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden bg-slate-50 dark:bg-slate-950 shadow-sm">
                                  <div 
                                    onClick={() => setCollapsedFiles(prev => ({...prev, [file.file]: !isCollapsed}))}
                                    className="bg-slate-100 dark:bg-slate-800 p-4 font-mono text-sm font-semibold border-b border-slate-200 dark:border-slate-800 flex justify-between items-center text-slate-700 dark:text-slate-300 cursor-pointer hover:bg-slate-200 dark:hover:bg-slate-700 transition select-none">
                                    <div className="flex items-center gap-2">
                                        {isCollapsed ? <ChevronRight className="w-5 h-5 text-indigo-500" /> : <ChevronDown className="w-5 h-5 text-indigo-500" />}
                                        <span>{file.file}</span>
                                        <span className="ml-2 bg-indigo-50 text-indigo-700 border border-indigo-200 px-2 py-0.5 rounded-full text-xs font-bold tracking-wide">
                                           {file.diff.length} Değişiklik
                                        </span>
                                    </div>
                                    <div className="flex items-center gap-3">
                                        <button
                                          onClick={(e) => {
                                            e.stopPropagation();
                                            handleViewCodeDiff(file.file);
                                          }}
                                          className="px-3 py-1 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-lg shadow-sm hover:shadow transition flex items-center gap-1.5 cursor-pointer"
                                        >
                                          <FileCode className="w-3.5 h-3.5" /> Kod Görünümü / Farkı
                                        </button>
                                        <span className={`text-xs px-2 py-1 rounded-md uppercase font-bold shadow-sm border
                                          ${file.status === 'new_file' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 
                                          file.status === 'deleted_file' ? 'bg-red-50 text-red-700 border-red-200' : 'bg-amber-50 text-amber-700 border-amber-200'}
                                        `}>
                                          {file.status === 'new_file' ? 'YENİ EKLENDİ' : file.status === 'deleted_file' ? 'SİLİNDİ' : 'DEĞİŞTİRİLDİ'}
                                        </span>
                                    </div>
                                  </div>
                                  
                                  {!isCollapsed && (
                                     <div className="p-5 space-y-4 bg-white dark:bg-slate-900 border-t border-slate-100 dark:border-slate-800">
                                       <div className={`p-4 rounded-xl flex items-center gap-3 border ${file.file.endsWith('.xslt') ? 'bg-fuchsia-50 dark:bg-fuchsia-900/20 border-fuchsia-200 dark:border-fuchsia-800 text-fuchsia-800 dark:text-fuchsia-200' : file.file.endsWith('.xsd') ? 'bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800 text-blue-800 dark:text-blue-200' : file.file.endsWith('.sch') ? 'bg-rose-50 dark:bg-rose-900/20 border-rose-200 dark:border-rose-800 text-rose-800 dark:text-rose-200' : 'bg-slate-50 dark:bg-slate-900/50 border-slate-200 text-slate-800 dark:text-slate-200'}`}>
                                          {file.file.endsWith('.xslt') && <Palette className="w-8 h-8 shrink-0" />}
                                          {file.file.endsWith('.xsd') && <Box className="w-8 h-8 shrink-0" />}
                                          {file.file.endsWith('.sch') && <ShieldAlert className="w-8 h-8 shrink-0" />}
                                          <div>
                                              <p className="font-bold">
                                                  {file.file.endsWith('.xslt') ? 'GÖRSEL TASARIM DEĞİŞİKLİĞİ' : file.file.endsWith('.xsd') ? 'YAPI (İSKELET) DEĞİŞİKLİĞİ' : file.file.endsWith('.sch') ? 'ŞEMATRON (KURAL) DEĞİŞİKLİĞİ' : 'DİĞER DEĞİŞİKLİKLER'}
                                              </p>
                                              <p className="text-sm mt-1 opacity-90">
                                                  {file.file.endsWith('.xslt') ? 'Bu dosyadaki değişiklikler faturanın PDF/HTML görünümünü etkiler. Zirve\'den gönderilen faturanın XML verisini bozmaz, sadece görseli etkiler.' : 
                                                   file.file.endsWith('.xsd') ? 'Bu dosya faturanın iskeletini etkiler. Zirve\'den giden faturada yeni bir alan (etiket) zorunlu kılınmış veya kaldırılmış olabilir. Kritik test gerektirir!' : 
                                                   file.file.endsWith('.sch') ? 'Bu değişiklikler faturanın GİB portali kontrollerini etkiler. Zirve\'den giden XML aynı kalsa bile, portale belgeyi reddecek veya uyarı verecek yeni bir kural eklenmiş olabilir.' : 'Standart bir paket dosyası güncellendi.'}
                                              </p>
                                          </div>
                                       </div>
                                       {file.diff.length === 0 && <p className="text-sm text-slate-500 dark:text-slate-400 italic p-3 bg-slate-50 dark:bg-slate-950 rounded-lg">Ana dosya eklendi veya kaldırıldı. (Kapsayıcı değişiklik)</p>}
                                {file.diff.map((diffItem, dIdx) => (
                                   <div key={dIdx} className={`p-4 rounded-xl text-sm border ${
                                      diffItem.type.includes('added') ? 'bg-emerald-50/50 border-emerald-200 text-emerald-900' :
                                      diffItem.type.includes('removed') ? 'bg-red-50/50 border-red-200 text-red-900' : 
                                      'bg-amber-50/50 border-amber-200 text-amber-900'
                                   }`}>
                                      <div className="flex items-center gap-2 mb-2">
                                        {diffItem.type.includes('added') && <div className="w-2 h-2 rounded-full bg-emerald-500"></div>}
                                        {diffItem.type.includes('removed') && <div className="w-2 h-2 rounded-full bg-red-500"></div>}
                                        {diffItem.type.includes('modified') && <div className="w-2 h-2 rounded-full bg-amber-500"></div>}
                                        <p className="font-bold text-base">{diffItem.target}</p>
                                      </div>
                                      <p className="text-slate-800 dark:text-slate-200 ml-4 font-semibold text-base mb-1">{diffItem.human_readable || diffItem.message}</p>
                                      <p className="text-slate-500 dark:text-slate-400 ml-4 text-xs">Teknik Log: {diffItem.message}</p>
                                      
                                      {diffItem.xpath && (
                                        <details className="mt-3 ml-4">
                                           <summary className="text-xs text-slate-500 dark:text-slate-400 cursor-pointer hover:text-indigo-600 font-semibold transition-colors">Teknik XPath Yolu Göster...</summary>
                                           <div className="mt-2 p-3 bg-slate-800 text-slate-300 rounded-lg text-xs font-mono break-all overflow-x-auto shadow-inner">
                                             {diffItem.xpath}
                                           </div>
                                        </details>
                                      )}
                                   </div>
                                ))}
                              </div>
                           )}
                               </div>
                             );
                          })}
                      </div>
                    )}
                 </div>
               )}

               {activeTab === 'scenarios' && (
                  <div className="p-0">
                     <table className="w-full text-left text-sm whitespace-nowrap md:whitespace-normal">
                        <thead className="bg-slate-50 dark:bg-slate-950 border-b border-slate-200 dark:border-slate-800 text-slate-500 dark:text-slate-400 font-semibold sticky top-0">
                           <tr>
                             <th className="p-4 w-1/4">Hedef (XSD/Element)</th>
                             <th className="p-4 w-[15%]">Değişim Tipi</th>
                             <th className="p-4 w-[30%] text-emerald-700">Pozitif Senaryo</th>
                             <th className="p-4 w-[30%] text-red-700">Negatif Senaryo</th>
                           </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                           {results.scenarios.map((scen, idx) => (
                             <tr key={idx} className="hover:bg-slate-50 dark:hover:bg-slate-900/50 transition-colors">
                               <td className="p-4 align-top">
                                 <p className="font-semibold text-slate-800 dark:text-slate-200 break-all">{scen.target}</p>
                                 <p className="text-xs text-slate-400 mt-1 break-all">{scen.file}</p>
                               </td>
                               <td className="p-4 align-top">
                                 <span className="inline-block px-2 py-1 bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 rounded-md text-xs font-bold whitespace-nowrap">
                                   {scen.type}
                                 </span>
                               </td>
                               <td className="p-4 align-top text-emerald-900 dark:text-emerald-300 leading-relaxed bg-emerald-50 dark:bg-emerald-950 bg-opacity-30 dark:bg-opacity-20">
                                 <div className="flex gap-2">
                                   <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0" />
                                   <p>{scen.positive}</p>
                                 </div>
                               </td>
                               <td className="p-4 align-top text-rose-900 dark:text-rose-300 leading-relaxed bg-rose-50 dark:bg-rose-950 bg-opacity-30 dark:bg-opacity-20">
                                 <div className="flex gap-2">
                                   <XCircle className="w-5 h-5 text-red-500 shrink-0" />
                                   <p>{scen.negative}</p>
                                 </div>
                               </td>
                             </tr>
                           ))}
                        </tbody>
                     </table>
                  </div>
               )}

            </div>
          </div>
        )}
        </div>

        {/* SCHEMATRON TAB */}
        <div className={activeMainTab === 'schematron' ? 'block' : 'hidden'}>
          <div className="bg-white dark:bg-slate-900 rounded-2xl p-8 shadow-sm border border-slate-200 dark:border-slate-800 mb-8 max-w-4xl mx-auto">
            <div className="text-center mb-10">
              <h2 className="text-2xl font-bold mb-2">Şematron Doğrulama</h2>
              <p className="text-slate-500 dark:text-slate-400">e-Fatura, e-İrsaliye gibi UBL XML belgelerinizi güncel Şematron (.sch) kurallarına göre doğrulayın.</p>
            </div>

            <div className="flex gap-6 mb-8">
              <div className="flex-1">
                <label className="block text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">XML Belgesi (.xml)</label>
                <div className="relative border-2 border-dashed border-slate-300 dark:border-slate-700 rounded-xl p-8 text-center hover:bg-slate-50 dark:bg-slate-950 hover:border-emerald-400 transition-colors cursor-pointer" onClick={() => document.getElementById('sch-xml-file').click()}>
                  <input id="sch-xml-file" type="file" accept=".xml" className="hidden" onChange={(e) => handleSchFileChange(e, 'xml')} />
                  <FileCode className={`w-12 h-12 mx-auto mb-3 ${schXmlFile ? 'text-emerald-600' : 'text-slate-400'}`} />
                  {schXmlFile ? (
                    <div>
                      <p className="font-semibold text-emerald-700">{schXmlFile.name}</p>
                      <p className="text-xs text-slate-500 dark:text-slate-400">{(schXmlFile.size / 1024).toFixed(2)} KB</p>
                    </div>
                  ) : (
                    <p className="text-slate-500 dark:text-slate-400 text-sm">Doğrulanacak XML dosyasını seçin.</p>
                  )}
                </div>
              </div>

              <div className="flex-1">
                <label className="block text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">Şematron Kuralları (.sch)</label>
                <div className="flex flex-col gap-3">
                   <select 
                      value={selectedSchFilename} 
                      onChange={(e) => { setSelectedSchFilename(e.target.value); setSchSchFile(null); }}
                      className="w-full p-4 font-semibold text-emerald-800 border-2 border-slate-300 dark:border-slate-700 rounded-xl bg-white dark:bg-slate-900 focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none transition-colors">
                      {savedSchematrons.map(f => (
                          <option key={f} value={f}>✅ Sistemdeki Hazır Kural: {f}</option>
                      ))}
                      <option value="">➕ Yeni/Farklı Şematron Dosyası Yükleyeceğim</option>
                   </select>

                   {!selectedSchFilename && (
                        <div className="relative border-2 border-dashed border-slate-300 dark:border-slate-700 rounded-xl p-4 text-center hover:bg-slate-50 dark:bg-slate-950 hover:border-emerald-400 transition-colors cursor-pointer" onClick={() => document.getElementById('sch-sch-file').click()}>
                          <input id="sch-sch-file" type="file" accept=".sch" className="hidden" onChange={(e) => { handleSchFileChange(e, 'sch'); setSelectedSchFilename(''); }} />
                          <Code2 className={`w-8 h-8 mx-auto mb-2 ${schSchFile ? 'text-emerald-600' : 'text-slate-400'}`} />
                          {schSchFile ? (
                            <p className="font-semibold text-emerald-700 text-sm truncate">{schSchFile.name}</p>
                          ) : (
                            <p className="text-slate-500 dark:text-slate-400 text-xs">Aygıttan .sch dosyası seçin.</p>
                          )}
                        </div>
                   )}
                   
                   {schSchFile && !selectedSchFilename && (
                        <button 
                            title="Sürekli aynı dosyayı yüklemek yerine sunucuya kaydedin ve menüden seçin"
                            onClick={handleUploadSchematron}
                            className="text-xs bg-indigo-50 text-indigo-700 border border-indigo-200 px-3 py-1.5 rounded-lg font-bold hover:bg-indigo-100 transition-colors self-end flex items-center gap-1 shadow-sm">
                            ⬆️ Bu Kuralı Sunucuya Kaydet
                        </button>
                   )}
                </div>
              </div>
            </div>

            {schError && (
              <div className="bg-red-50 text-red-600 p-4 rounded-lg flex items-center gap-3 mb-6">
                 <AlertCircle className="w-5 h-5" /> {schError}
              </div>
            )}

            <button 
              onClick={handleSchematronValidate} 
              disabled={schLoading || !schXmlFile || (!schSchFile && !selectedSchFilename)}
              className={`w-full py-4 rounded-xl flex items-center justify-center gap-2 font-bold text-lg transition-all ${
                schLoading || !schXmlFile || (!schSchFile && !selectedSchFilename)
                ? 'bg-slate-100 dark:bg-slate-800 text-slate-400 cursor-not-allowed' 
                : 'bg-emerald-600 text-white hover:bg-emerald-700 hover:shadow-lg shadow-emerald-600/30'
              }`}
            >
              {schLoading ? (
                <>
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-current" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                  Doğrulanıyor...
                </>
              ) : (
                <><CheckCircle2 className="w-5 h-5"/> XML'i Doğrula</>
              )}
            </button>
            
            {/* SCH RESULTS */}
            {schResults && (
              <div className="mt-8 border-t border-slate-200 dark:border-slate-800 pt-8">
                <div className={`p-4 rounded-xl border flex items-start gap-4 ${schResults.is_valid ? 'bg-emerald-50 border-emerald-200 text-emerald-900' : 'bg-red-50 border-red-200 text-red-900'}`}>
                  {schResults.is_valid ? <CheckCircle2 className="w-8 h-8 text-emerald-600 mt-1" /> : <XCircle className="w-8 h-8 text-red-600 mt-1" />}
                  <div>
                    <h3 className="font-bold text-lg">{schResults.is_valid ? 'Doğrulama Başarılı' : 'Doğrulama Başarısız: Hatalar Bulundu'}</h3>
                    <p className="mt-1 text-sm">{schResults.is_valid ? 'XML belgesi şematron kurallarından başarıyla geçti.' : `${schResults.errors?.length || 0} adet kural ihlali tespit edildi.`}</p>
                  </div>
                </div>
                
                {!schResults.is_valid && schResults.errors?.length > 0 && (
                  <div className="mt-6 space-y-4">
                    <h4 className="font-bold text-slate-700 dark:text-slate-300">Hata Detayları:</h4>
                    {schResults.errors.map((errItem, idx) => (
                      <div key={idx} className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg p-4">
                        <p className="font-semibold text-slate-800 dark:text-slate-200">{errItem.message}</p>
                        <div className="bg-slate-800 rounded-lg p-3 text-sm text-slate-300 font-mono overflow-auto break-all">
                           <p className="mb-2"><span className="text-slate-500">Konum (Location):</span> {errItem.location}</p>
                           <p className="mb-2"><span className="text-slate-500">Kural (Test):</span> {errItem.test}</p>
                           {errItem.value && (
                              <p className="text-amber-400 font-semibold"><span className="text-slate-500 font-normal">Sizin XML'deki Değeriniz (Value):</span> {errItem.value}</p>
                           )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
            
          </div>
        </div>

        {/* KVKK SANITIZER TAB */}
        <div className={activeMainTab === 'sanitizer' ? 'block' : 'hidden'}>
          <div className="bg-white dark:bg-slate-900 rounded-2xl p-8 shadow-sm border border-slate-200 dark:border-slate-800 mb-8 max-w-4xl mx-auto">
            <div className="text-center mb-10">
              <h2 className="text-2xl font-bold mb-2 text-amber-600 flex justify-center items-center gap-2"><ShieldCheck className="w-8 h-8"/> UBL XML XSLT İşlemleri</h2>
              <p className="text-slate-500 dark:text-slate-400">Canlı ortamdaki gerçek faturalarınızı ve hassas şirket/müşteri verilerinizi içeren .xml dosyalarını orijinal yapısını ve formatını bozmadan güvenle maskeleyin.</p>
            </div>

            <div className="mb-8">
                <label className="block text-sm font-semibold text-slate-700 dark:text-slate-300 mb-2">Gizlenecek Fatura / İrsaliye Belgesi (.xml)</label>
                <div className="relative border-2 border-dashed border-slate-300 dark:border-slate-700 rounded-xl p-8 text-center hover:bg-slate-50 dark:bg-slate-950 hover:border-amber-400 transition-colors cursor-pointer" onClick={() => document.getElementById('san-xml-file').click()}>
                  <input id="san-xml-file" type="file" accept=".xml" className="hidden" onChange={handleSanFileChange} />
                  <FileCode className={`w-12 h-12 mx-auto mb-3 ${sanFile ? 'text-amber-600' : 'text-slate-400'}`} />
                  {sanFile ? (
                    <div>
                      <p className="font-semibold text-amber-700">{sanFile.name}</p>
                      <p className="text-xs text-slate-500 dark:text-slate-400">{(sanFile.size / 1024).toFixed(2)} KB</p>
                    </div>
                  ) : (
                    <p className="text-slate-500 dark:text-slate-400 text-sm">Anonimleştirilecek XML dosyasını yüklemek için tıklayın.</p>
                  )}
                </div>
            </div>

            {sanError && (
              <div className="bg-red-50 text-red-600 p-4 rounded-lg flex items-center gap-3 mb-6">
                 <AlertCircle className="w-5 h-5" /> {sanError}
              </div>
            )}

            <button 
              onClick={handleSanitize} 
              disabled={sanLoading || !sanFile}
              className={`w-full py-4 rounded-xl flex items-center justify-center gap-2 font-bold text-lg transition-all ${
                sanLoading || !sanFile 
                ? 'bg-slate-100 dark:bg-slate-800 text-slate-400 cursor-not-allowed' 
                : 'bg-amber-600 text-white hover:bg-amber-700 hover:shadow-lg shadow-amber-600/30'
              }`}
            >
              {sanLoading ? (
                <>
                  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-current" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                  Anonimleştiriliyor...
                </>
              ) : (
                <><ShieldCheck className="w-5 h-5"/> Gizli Verileri Maskele ve Belgeyi İndir</>
              )}
            </button>
            
            {sanResult && (
              <div className="mt-8 border-t border-slate-200 dark:border-slate-800 pt-8">
                 <div className="bg-emerald-50 border border-emerald-200 text-emerald-900 px-6 py-4 rounded-2xl w-full flex flex-col items-center text-center shadow-sm mb-6">
                    <CheckCircle2 className="w-10 h-10 text-emerald-500 mx-auto mb-2" />
                    <h3 className="font-bold text-lg mb-1">Maskeleme Başarıyla Tamamlandı!</h3>
                    <p className="text-sm mb-4">TCKN, VKN, İsim, Telefon ve Adres gibi hassas veriler geçersiz (dummy) test verileriyle değiştirildi. Belgenin yapısı korundu.</p>
                    <button 
                      onClick={downloadSanitizedXml}
                      className="inline-flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white font-bold py-3 px-6 rounded-xl transition-colors shadow-md w-full max-w-sm">
                       <Download className="w-5 h-5"/> Anonim XML'i İndir
                    </button>
                 </div>

                 <div className="border border-slate-200 dark:border-slate-700 rounded-xl overflow-hidden bg-white dark:bg-slate-900 shadow-sm">
                    <div className="bg-slate-100 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 p-3 font-semibold text-sm text-slate-700 dark:text-slate-300 flex items-center gap-2">
                       <FileCode className="w-4 h-4"/> Maskelenmiş Belge Önizlemesi (XSLT Render)
                    </div>
                    {sanResult.html_preview && !sanResult.html_preview.includes('Önizleme Oluşturulamadı') ? (
                         <iframe 
                            srcDoc={sanResult.html_preview}
                            className="w-full h-[600px] border-none bg-white"
                            title="XSLT Preview"
                         />
                    ) : (
                        <div className="p-8 text-center text-slate-500 bg-slate-50 dark:bg-slate-950 h-48 flex items-center justify-center">
                           <div>
                              <AlertCircle className="w-8 h-8 mx-auto mb-2 text-slate-400" />
                              <p>Bu belgede geçerli bir görselleştirme (XSLT) dosyası bulunamadı, ancak XML olarak indirebilirsiniz.</p>
                           </div>
                        </div>
                    )}
                 </div>
              </div>
            )}

          </div>
        </div>

        {/* FATURA RÖNTGENİ (X-RAY) SECTION */}
        {activeMainTab === 'xray' && (
          <div className="space-y-6 animate-fadeIn">
            {!xrayResult ? (
              <div className="bg-white dark:bg-slate-900 rounded-2xl p-8 shadow-sm border border-slate-200 dark:border-slate-800 mb-8 max-w-4xl mx-auto">
                <div className="text-center mb-10">
                  <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-violet-100 dark:bg-violet-950/50 text-violet-600 dark:text-violet-400 mb-4 animate-bounce">
                    <Search className="w-8 h-8" />
                  </div>
                  <h2 className="text-2xl font-bold mb-2">Fatura Röntgeni (X-Ray)</h2>
                  <p className="text-slate-500 dark:text-slate-400 max-w-lg mx-auto">
                    Herhangi bir UBL XML fatura dosyasını yükleyin. Fatura tasarım görseli (XSLT) üzerinden metinleri seçerek arka plandaki XML yolu (XPath) adreslerini anında bulun.
                  </p>
                </div>

                <div 
                  className="border-2 border-dashed border-violet-300 dark:border-violet-800 rounded-2xl p-12 text-center hover:bg-violet-50/50 dark:hover:bg-violet-950/10 hover:border-violet-500 transition-all cursor-pointer bg-white dark:bg-slate-950/30 group" 
                  onClick={() => document.getElementById('xray-file').click()}
                >
                  <input id="xray-file" type="file" accept=".xml" className="hidden" onChange={handleXrayFileChange} />
                  <FileCode className="w-16 h-16 mx-auto mb-4 text-slate-400 group-hover:text-violet-500 transition-colors" />
                  
                  {xrayFile ? (
                    <div>
                      <p className="font-bold text-lg text-violet-700 dark:text-violet-400">{xrayFile.name}</p>
                      <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">{(xrayFile.size / 1024).toFixed(2)} KB</p>
                    </div>
                  ) : (
                    <div>
                      <p className="text-slate-700 dark:text-slate-300 font-semibold mb-1 text-base">Faturayı buraya sürükleyin veya tıklayarak seçin</p>
                      <p className="text-slate-400 text-xs">Sadece UBL XML formatı desteklenmektedir.</p>
                    </div>
                  )}
                </div>

                {xrayError && (
                  <div className="bg-red-50 dark:bg-red-950/20 text-red-600 dark:text-red-400 p-4 rounded-xl flex items-center gap-3 mt-6">
                     <AlertCircle className="w-5 h-5 flex-shrink-0" />
                     <p className="text-sm font-medium">{xrayError}</p>
                  </div>
                )}

                <div className="mt-8 flex justify-center">
                  <button
                    onClick={() => handleXrayUpload()}
                    disabled={xrayFileLoading || !xrayFile}
                    className={`w-full max-w-md py-4 rounded-xl flex items-center justify-center gap-2 font-bold text-lg transition-all ${
                      xrayFileLoading || !xrayFile 
                      ? 'bg-slate-100 dark:bg-slate-800 text-slate-400 cursor-not-allowed' 
                      : 'bg-violet-600 text-white hover:bg-violet-700 hover:shadow-lg shadow-violet-600/30'
                    }`}
                  >
                    {xrayFileLoading ? (
                      <>
                        <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-current" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                        Fatura Okunuyor & Görselleştiriliyor...
                      </>
                    ) : (
                      <><Search className="w-5 h-5"/> Faturayı Görselleştir ve Röntgeni Başlat</>
                    )}
                  </button>
                </div>
              </div>
            ) : (
              <div 
                ref={containerRef}
                className="flex gap-4 items-stretch relative"
                style={{ cursor: isDragging ? 'col-resize' : 'default', userSelect: isDragging ? 'none' : 'auto' }}
              >
                {/* LEFT SIDE: PREVIEW */}
                <div 
                  className="border border-slate-200 dark:border-slate-800 rounded-2xl overflow-hidden bg-white dark:bg-slate-900 shadow-sm flex flex-col shrink-0 animate-fadeIn"
                  style={{ width: `${leftWidth}%` }}
                >
                  <div className="bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 p-4 font-semibold text-sm text-slate-700 dark:text-slate-300 flex items-center justify-between">
                     <div className="flex items-center gap-2">
                        <FileCode className="w-5 h-5 text-violet-500"/>
                        <span className="font-bold">Fatura Görsel Önizlemesi (XSLT Tasarımı)</span>
                        <span className="bg-violet-100 text-violet-800 dark:bg-violet-950 dark:text-violet-300 text-xs px-2 py-0.5 rounded-full font-medium ml-2 max-w-[200px] truncate">{xrayResult.filename}</span>
                     </div>
                     <button
                       onClick={() => {
                         setXrayResult(null);
                         setXrayFile(null);
                         setXrayResults(null);
                         setXraySelectedText("");
                       }}
                       className="text-xs text-slate-500 hover:text-red-500 font-bold border border-slate-200 dark:border-slate-800 hover:border-red-200 px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1 bg-white dark:bg-slate-950"
                     >
                       <XCircle className="w-3.5 h-3.5" /> Başka Fatura Yükle
                     </button>
                  </div>
                  
                  {xrayResult.html_preview ? (
                     <iframe 
                        srcDoc={xrayResult.html_preview}
                        onLoad={(e) => handleIframeLoad(e, xrayResult.xml_base64)}
                        className="w-full h-[700px] border-none bg-white"
                        title="XSLT Röntgen Preview"
                     />
                  ) : (
                     <div className="p-12 text-center text-slate-500 bg-slate-50 dark:bg-slate-950 h-[400px] flex items-center justify-center">
                        <div>
                           <AlertCircle className="w-12 h-12 mx-auto mb-2 text-slate-400 animate-pulse" />
                           <p className="font-bold text-lg text-slate-700 dark:text-slate-300 mb-1">Tasarım Bulunamadı</p>
                           <p className="text-sm">Bu XML faturada gömülü bir XSLT tasarımı tespit edilemedi.</p>
                        </div>
                     </div>
                  )}
                </div>

                {/* DRAGGABLE RESIZER HANDLE */}
                <div 
                  onMouseDown={startResizing}
                  className={`w-2.5 hover:w-3.5 cursor-col-resize self-stretch flex items-center justify-center transition-all select-none group shrink-0 rounded-full ${
                    isDragging ? 'bg-violet-600 shadow-lg shadow-violet-600/35 scale-x-125' : 'bg-slate-100 dark:bg-slate-800/80 hover:bg-violet-400 dark:hover:bg-violet-500/80'
                  }`}
                  title="Genişliği Ayarlamak İçin Sürükleyin"
                >
                  <div className="flex flex-col gap-1 items-center justify-center">
                    <span className={`w-1 h-1 rounded-full ${isDragging ? 'bg-violet-100' : 'bg-slate-400 group-hover:bg-violet-100'}`}></span>
                    <span className={`w-1 h-1 rounded-full ${isDragging ? 'bg-violet-100' : 'bg-slate-400 group-hover:bg-violet-100'}`}></span>
                    <span className={`w-1 h-1 rounded-full ${isDragging ? 'bg-violet-100' : 'bg-slate-400 group-hover:bg-violet-100'}`}></span>
                  </div>
                </div>

                {/* RIGHT SIDE: INTERACTIVE XML CODE BROWSER */}
                <div 
                  className="flex flex-col border border-slate-200 dark:border-slate-800 rounded-2xl bg-white dark:bg-slate-900 shadow-sm p-5 h-[756px] shrink-0"
                  style={{ width: `${100 - leftWidth}%` }}
                >
                  <h3 className="text-md font-bold text-slate-800 dark:text-slate-200 mb-2 flex items-center justify-between">
                     <span className="flex items-center gap-2">
                        <Code2 className="w-5 h-5 text-violet-500 animate-pulse" />
                        UBL XML Kaynak Kodu
                     </span>
                     <span className="bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 text-xs px-2.5 py-0.5 rounded-full font-medium">
                        {xmlText.split('\n').length} satır
                     </span>
                  </h3>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400 mb-4 leading-relaxed">
                     Sol taraftaki fatura şablonu üzerinden metin seçin; XML kodunda otomatik olarak ilgili satıra odaklanacaktır.
                  </p>

                  {/* ACTIVE SELECTIONS & MATCHES NAVIGATION DOCK */}
                  {xrayResults && xrayResults.length > 0 && (
                     <div className="bg-violet-50 dark:bg-violet-950/20 border border-violet-100 dark:border-violet-900/50 rounded-xl p-3 mb-4 flex flex-col gap-2 shrink-0">
                        <div className="flex items-center justify-between text-xs font-bold">
                           <span className="text-violet-700 dark:text-violet-400">🔍 "{xraySelectedText}" İçin {xrayResults.length} Eşleşme</span>
                        </div>
                        <div className="flex flex-col gap-1.5 max-h-32 overflow-y-auto pr-1">
                           {xrayResults.map((res, i) => {
                              const isCurrent = highlightedLine === res.line;
                              return (
                                 <button
                                    key={i}
                                    onClick={() => {
                                       setHighlightedLine(res.line);
                                       const lineElem = document.getElementById(`xml-line-${res.line}`);
                                       if (lineElem) {
                                          lineElem.scrollIntoView({ behavior: 'smooth', block: 'center' });
                                       }
                                    }}
                                    className={`text-left text-[11px] p-2 rounded-lg transition-all flex items-center justify-between border ${
                                       isCurrent 
                                       ? 'bg-violet-600 text-white font-semibold border-violet-600 shadow-sm shadow-violet-600/30' 
                                       : 'bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-300 border-slate-200 dark:border-slate-800 hover:bg-slate-100 dark:hover:bg-slate-800'
                                    }`}
                                 >
                                    <div className="flex flex-col flex-1 min-w-0 pr-2">
                                       <span className="truncate font-mono font-bold leading-tight">{res.xpath.split('/').pop()}</span>
                                       <span className={`text-[9px] truncate opacity-80 font-mono mt-0.5 ${isCurrent ? 'text-violet-200' : 'text-slate-400'}`}>{res.xpath}</span>
                                    </div>
                                    <span className={`text-[9px] font-bold px-2 py-0.5 rounded-full shrink-0 ${
                                       isCurrent ? 'bg-violet-900 text-white' : 'bg-slate-100 dark:bg-slate-800 text-slate-500'
                                    }`}>Satır {res.line}</span>
                                 </button>
                              );
                           })}
                        </div>
                     </div>
                  )}

                  {/* XML CODE CONTAINER */}
                  <div className="flex-1 overflow-auto bg-slate-950 text-slate-100 rounded-xl p-4 font-mono text-[10px] leading-normal border border-slate-800 shadow-inner relative flex flex-col">
                     {xmlText ? (
                        <div className="space-y-0.5">
                           {xmlText.split('\n').map((line, index) => {
                              const lineNum = index + 1;
                              const isHighlighted = highlightedLine === lineNum;
                              return (
                                 <div 
                                    key={index}
                                    id={`xml-line-${lineNum}`}
                                    className={`flex items-start transition-all duration-500 py-0.5 px-2 rounded-md ${
                                      isHighlighted 
                                      ? 'bg-violet-950/80 border-l-4 border-violet-500 font-bold text-violet-200 shadow-lg ring-1 ring-violet-500/30 py-1' 
                                      : 'hover:bg-slate-900/50'
                                    }`}
                                 >
                                    <span className={`w-8 select-none text-right pr-2 mr-3 border-r shrink-0 ${
                                      isHighlighted 
                                      ? 'text-violet-400 border-violet-500 font-bold' 
                                      : 'text-slate-700 border-slate-900'
                                    }`}>
                                       {lineNum}
                                    </span>
                                    <span className={`whitespace-pre-wrap break-all flex-1 ${
                                      isHighlighted ? 'text-violet-100' : 'text-slate-300'
                                    }`}>
                                       {line}
                                    </span>
                                 </div>
                              );
                           })}
                        </div>
                     ) : (
                        <div className="flex-1 flex items-center justify-center text-center p-6 text-slate-500">
                           XML Kodları Okunamadı.
                        </div>
                     )}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ASSISTANT SECTION */}
        {activeMainTab === 'assistant' && (
          <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-800 overflow-hidden">
             <div className="flex h-[750px]">
                {/* LEFTSIDE: TEACH BOT & API KEY */}
                <div className="w-1/3 border-r border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 p-6 flex flex-col">
                   {isApiKeySaved ? (
                      <div className="mb-6 p-4 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-sm flex items-center justify-between">
                         <div className="flex items-center gap-3">
                            <CheckCircle2 className="w-6 h-6 text-emerald-500" />
                            <div>
                               <p className="text-sm font-bold text-slate-800 dark:text-slate-200">API Anahtarı Aktif</p>
                               <p className="text-xs text-slate-500 dark:text-slate-400">Asistan şu anda kullanıma hazır.</p>
                            </div>
                         </div>
                         <button 
                           onClick={() => setIsApiKeySaved(false)}
                           className="p-2 text-slate-400 hover:text-indigo-600 hover:bg-slate-50 dark:bg-slate-950 rounded-lg transition-colors border border-transparent hover:border-indigo-100"
                           title="API Anahtarını Düzenle">
                           <Edit2 className="w-4 h-4" />
                         </button>
                      </div>
                   ) : (
                      <div className="mb-6 p-4 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl shadow-sm">
                         <label className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-2">Google Gemini API Key</label>
                         <div className="flex gap-2">
                            <input 
                              type="password" 
                              value={geminiKey}
                              onChange={(e) => setGeminiKey(e.target.value)}
                              placeholder="AIzaSy..." 
                              className="flex-1 w-full text-xs font-mono border border-slate-300 dark:border-slate-700 rounded-lg px-3 py-2 focus:ring-1 focus:ring-indigo-500 outline-none bg-transparent" 
                            />
                            <button 
                              onClick={handleSaveApiKey}
                              disabled={keyLoading || !geminiKey.trim()}
                              className="px-3 py-2 bg-slate-800 text-white text-xs font-bold rounded-lg hover:bg-slate-900 disabled:opacity-50 transition-colors">
                              {keyLoading ? '...' : 'Kaydet'}
                            </button>
                         </div>
                         <p className="text-[10px] text-slate-500 dark:text-slate-400 mt-2 leading-tight">Bu şifre ekibiniz için <code className="bg-slate-100 dark:bg-slate-800 rounded px-1">.env</code> dosyasına yerleşecektir ve herkes kullanabilecektir.</p>
                      </div>
                   )}
                   
                   <hr className="border-slate-200 dark:border-slate-800 mb-6" />

                   <h3 className="font-bold text-slate-800 dark:text-slate-200 mb-2 flex items-center gap-2"><BookOpen className="w-5 h-5 text-indigo-600"/> Asistanı Eğit (Kılavuz Yükle)</h3>
                   <p className="text-xs text-slate-500 dark:text-slate-400 mb-6">GİB'in yayınladığı Tekli Kılavuz (PDF) veya Toplu Kılavuzları içeren (ZIP) arşiv yükleyerek yapay zekanın en güncel kuralları topluca öğrenmesini sağlayın.</p>
                   
                   <div className="border-2 border-dashed border-slate-300 dark:border-slate-700 rounded-xl p-4 text-center hover:bg-slate-100 dark:bg-slate-800 hover:border-indigo-400 transition-colors cursor-pointer mb-4 bg-white dark:bg-slate-900" onClick={() => document.getElementById('pdf-upload').click()}>
                      <input id="pdf-upload" type="file" accept=".pdf,.zip" className="hidden" onChange={handlePdfChange} />
                      {pdfFile ? (
                         <p className="font-semibold text-indigo-700 text-sm truncate">{pdfFile.name}</p>
                      ) : (
                         <p className="text-slate-500 dark:text-slate-400 text-sm">PDF Veya ZIP seçmek için tıklayın.</p>
                      )}
                   </div>
                   
                   <button 
                      onClick={handleIngestPdf} 
                      disabled={pdfUploadLoading || !pdfFile}
                      className={`w-full py-3 rounded-xl flex items-center justify-center gap-2 font-bold text-sm transition-all shadow-sm ${
                         pdfUploadLoading || !pdfFile ? 'bg-slate-200 text-slate-400 cursor-not-allowed' : 'bg-indigo-600 text-white hover:bg-indigo-700'
                      }`}>
                      {pdfUploadLoading ? (
                        <> <Activity className="w-4 h-4 animate-spin"/> Milyonlarca kural işleniyor... </>
                      ) : 'Veritabanına Ekle ve Eğit'}
                    </button>

                    {pdfUploadLoading && (
                      <div className="mt-4 p-4 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl space-y-3 shadow-sm transition-all duration-300">
                        <div className="flex justify-between items-center text-xs font-bold">
                          <span className="text-indigo-600 dark:text-indigo-400 flex items-center gap-1.5">
                            {uploadProgress < 100 ? (
                              <>
                                <span className="w-2.5 h-2.5 rounded-full bg-indigo-600 animate-ping"></span>
                                📁 Dosya Sunucuya Yükleniyor...
                              </>
                            ) : (
                              <>
                                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></span>
                                ⚡ Yapay Zeka Kuralları Öğreniyor...
                              </>
                            )}
                          </span>
                          <span className="font-mono text-slate-600 dark:text-slate-400">
                            {uploadProgress < 100 ? `%${uploadProgress}` : `%${learningProgress}`}
                          </span>
                        </div>
                        <div className="w-full bg-slate-100 dark:bg-slate-800 rounded-full h-2 overflow-hidden shadow-inner relative">
                          <div 
                            className={`h-full rounded-full transition-all duration-300 ${
                              uploadProgress < 100 
                                ? 'bg-gradient-to-r from-indigo-500 to-violet-600' 
                                : 'bg-gradient-to-r from-emerald-500 to-teal-600 animate-pulse'
                            }`} 
                            style={{ width: `${uploadProgress < 100 ? uploadProgress : (learningProgress === 0 ? 5 : learningProgress)}%` }}
                          ></div>
                        </div>
                        <p className="text-[10px] text-slate-500 dark:text-slate-400 leading-tight">
                          {uploadProgress < 100 
                            ? 'Dosya transferi yapılıyor, lütfen tarayıcıyı kapatmayın.' 
                            : 'Dosya başarıyla yüklendi! Yapay zeka PDF kılavuzundaki binlerce kuralı okuyor ve vektör veritabanına eğitiyor. Bu işlem birkaç saniye sürebilir...'}
                        </p>
                      </div>
                    )}

                    <div className="mt-8 p-4 bg-blue-50/50 dark:bg-blue-950/20 border border-blue-100 dark:border-blue-900/50 rounded-xl text-xs text-blue-800 dark:text-blue-200 leading-relaxed shadow-sm">
                       <strong>Bilgi:</strong> Akıllı GİB Asistanı, kendi hafızasını (Vektör DB) kullanır. Sorularınızı yanıtlarken en son yüklediğiniz <b>Kılavuzlara</b> dayanarak %100 doğrulukla ve halüsinasyon yapmadan cevap vermeye çalışır.
                    </div>
                    <a 
                      href="http://localhost:3001" 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="mt-4 p-3 bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 hover:bg-slate-200 dark:hover:bg-slate-700 text-xs font-bold rounded-xl text-slate-700 dark:text-slate-300 transition flex items-center justify-center gap-2 shadow-sm cursor-pointer"
                    >
                      <Activity className="w-4 h-4 text-indigo-500 animate-pulse" /> VectorDB Görsel Yönetim Paneli
                    </a>
                    <div className="mt-auto opacity-30 pointer-events-none mx-auto mb-4">
                        <Cpu className="w-24 h-24 text-slate-400" />
                    </div>

                </div>

                {/* RIGHTSIDE: CHAT INTERFACE */}
                <div className="w-2/3 flex flex-col bg-slate-50 dark:bg-slate-950 relative">
                   {chatMessages.length === 0 && (
                      <div className="absolute inset-0 flex flex-col items-center justify-center p-8 text-center pointer-events-none">
                         <MessageSquare className="w-16 h-16 text-slate-200 mb-4" />
                         <h3 className="text-xl font-bold text-slate-400 mb-2">GİB Asistanı'na Soru Sorun</h3>
                         <p className="text-sm text-slate-400 max-w-sm">Sol pencereden gerekli Kılavuz dosyalarını yükledikten sonra, test süreçlerinizle ilgili dilediğiniz e-Dönüşüm kuralını sorabilirsiniz.</p>
                      </div>
                   )}
                   <div className="flex-1 overflow-y-auto p-6 space-y-4 z-10">
                      {chatMessages.map((msg, idx) => (
                         <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                            <div className={`max-w-[85%] rounded-2xl p-4 text-sm shadow-sm ${
                               msg.role === 'user' ? 'bg-indigo-600 text-white rounded-br-none' : 'bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-200 rounded-bl-none border border-slate-200 dark:border-slate-800'
                            }`}>
                               <div style={{whiteSpace: 'pre-wrap', lineHeight: '1.6'}}>
                                  {msg.text === '' && msg.role === 'bot' ? (
                                     <span className="text-slate-500 dark:text-slate-400 italic flex items-center gap-2 font-medium">
                                        <Search className="w-4 h-4 animate-pulse text-indigo-500" />
                                        Mevzuatı Kontrol Ediyorum...
                                     </span>
                                  ) : (
                                     msg.text
                                  )}
                               </div>
                            </div>
                         </div>
                      ))}
                      {chatLoading && (!chatMessages.length || chatMessages[chatMessages.length - 1].text !== '') && (
                         <div className="flex justify-start">
                            <div className="bg-white dark:bg-slate-900 text-slate-500 dark:text-slate-400 rounded-2xl rounded-bl-none p-4 text-sm max-w-[80%] border border-slate-200 dark:border-slate-800 flex items-center gap-2 shadow-sm">
                               <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce"></div>
                               <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
                               <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{animationDelay: '0.4s'}}></div>
                            </div>
                         </div>
                      )}
                      <div ref={messagesEndRef} />
                   </div>
                   
                   <ChatInputBox onSend={handleSendChatStream} loading={chatLoading} />
                </div>
             </div>
          </div>
        )}

        {/* RECONCILIATION SECTION */}
        {activeMainTab === 'reconciliation' && (
          <div className="space-y-8 animate-fadeIn">
            <div className="bg-white dark:bg-slate-900 rounded-2xl p-6 shadow-sm border border-slate-200 dark:border-slate-800">
              <h2 className="text-2xl font-bold mb-2 text-slate-800 dark:text-white flex items-center gap-2">
                <Activity className="w-7 h-7 text-rose-500" /> Veritabanı ve XML Mutabakat Testi
              </h2>
              <p className="text-slate-500 dark:text-slate-400 text-sm leading-relaxed">
                Zirve Yazılım SQL Server test veritabanınızdaki (<code className="bg-slate-100 dark:bg-slate-800 px-1 py-0.5 rounded font-mono text-rose-500">zirvegenel.mdf</code> ve <code className="bg-slate-100 dark:bg-slate-800 px-1 py-0.5 rounded font-mono text-rose-500">[Yıl]T.mdf</code>) fatura ve satır kayıtları ile UBL XML çıktısını kıyaslayarak veri kayıplarını ve yuvarlama farklarını denetleyin.
              </p>
            </div>

            <div className="flex flex-col lg:flex-row gap-8">
              {/* LEFT CONFIG COLUMN */}
              <div className="w-full lg:w-1/3 bg-white dark:bg-slate-900 rounded-2xl p-6 shadow-sm border border-slate-200 dark:border-slate-800 space-y-6 h-fit">
                <h3 className="text-lg font-bold text-slate-800 dark:text-white border-b border-slate-100 dark:border-slate-800 pb-3 flex items-center gap-2">
                  <Cpu className="w-5 h-5 text-indigo-500" /> SQL Sunucu & Firma Ayarları
                </h3>
                
                <form onSubmit={handleReconcileSubmit} className="space-y-4">
                  <div>
                    <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-2">SQL Server Instance</label>
                    <div className="flex gap-2">
                      <input 
                        type="text" 
                        value={reconConfig.server} 
                        onChange={e => setReconConfig(prev => ({...prev, server: e.target.value}))}
                        className="flex-1 px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 focus:ring-2 focus:ring-rose-500 focus:outline-none transition-all dark:text-white"
                        placeholder="localhost\SQLEXPRESS" 
                        required
                      />
                      <button
                        type="button"
                        onClick={handleFetchCompanies}
                        disabled={reconDbLoading}
                        className="px-4 py-2 bg-slate-100 hover:bg-slate-200 dark:bg-slate-850 dark:hover:bg-slate-800 dark:text-white text-xs font-bold rounded-xl transition border border-slate-200 dark:border-slate-800 cursor-pointer shrink-0"
                      >
                        {reconDbLoading ? "..." : "Firmaları Yükle"}
                      </button>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-2">Firma Kodu</label>
                      {reconCompanies.length > 0 ? (
                        <select
                          value={reconConfig.company_code}
                          onChange={e => {
                            setReconConfig(prev => ({...prev, company_code: e.target.value}));
                            handleFetchYears(e.target.value);
                          }}
                          className="w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 focus:ring-2 focus:ring-rose-500 focus:outline-none transition-all dark:text-white font-semibold cursor-pointer"
                        >
                          {reconCompanies.map((c, idx) => (
                            <option key={idx} value={c}>{c}</option>
                          ))}
                        </select>
                      ) : (
                        <input 
                          type="text" 
                          value={reconConfig.company_code} 
                          onChange={e => setReconConfig(prev => ({...prev, company_code: e.target.value}))}
                          className="w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 focus:ring-2 focus:ring-rose-500 focus:outline-none transition-all dark:text-white"
                          placeholder="GÖRKEM_KOLAY" 
                          required
                        />
                      )}
                    </div>
                    <div>
                      <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-2">Çalışma Yılı</label>
                      {reconYears.length > 0 ? (
                        <select
                          value={reconConfig.year}
                          onChange={e => setReconConfig(prev => ({...prev, year: e.target.value}))}
                          className="w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 focus:ring-2 focus:ring-rose-500 focus:outline-none transition-all dark:text-white font-semibold cursor-pointer"
                        >
                          {reconYears.map((y, idx) => (
                            <option key={idx} value={y}>{y}</option>
                          ))}
                        </select>
                      ) : (
                        <input 
                          type="text" 
                          value={reconConfig.year} 
                          onChange={e => setReconConfig(prev => ({...prev, year: e.target.value}))}
                          className="w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 focus:ring-2 focus:ring-rose-500 focus:outline-none transition-all dark:text-white"
                          placeholder="2026" 
                          required
                        />
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-2 py-2">
                    <input 
                      type="checkbox" 
                      id="trusted_conn" 
                      checked={reconConfig.trusted}
                      onChange={e => setReconConfig(prev => ({...prev, trusted: e.target.checked}))}
                      className="w-4 h-4 text-rose-600 focus:ring-rose-500 border-slate-300 rounded"
                    />
                    <label htmlFor="trusted_conn" className="text-sm font-semibold text-slate-700 dark:text-slate-300 select-none cursor-pointer">Windows Kimlik Doğrulaması (Trusted)</label>
                  </div>

                  {!reconConfig.trusted && (
                    <div className="space-y-4 animate-fadeIn">
                      <div>
                        <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-2">Kullanıcı Adı (SA)</label>
                        <input 
                          type="text" 
                          value={reconConfig.username} 
                          onChange={e => setReconConfig(prev => ({...prev, username: e.target.value}))}
                          className="w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 focus:ring-2 focus:ring-rose-500 focus:outline-none transition-all dark:text-white"
                        />
                      </div>
                      <div>
                        <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-2">Şifre</label>
                        <input 
                          type="password" 
                          value={reconConfig.password} 
                          onChange={e => setReconConfig(prev => ({...prev, password: e.target.value}))}
                          className="w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 focus:ring-2 focus:ring-rose-500 focus:outline-none transition-all dark:text-white"
                        />
                      </div>
                    </div>
                  )}

                  <div className="pt-4 border-t border-slate-100 dark:border-slate-800">
                    <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 mb-2">Karşılaştırılacak UBL XML Dosyası</label>
                    <div className="relative border-2 border-dashed border-slate-200 dark:border-slate-800 rounded-2xl p-4 text-center hover:border-rose-500 transition-colors">
                      <input 
                        type="file" 
                        accept=".xml"
                        onChange={e => setReconFile(e.target.files[0])}
                        className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                      />
                      <FileCode className="w-8 h-8 text-slate-400 mx-auto mb-2" />
                      <p className="text-xs font-bold text-slate-600 dark:text-slate-400 truncate">
                        {reconFile ? reconFile.name : "XML faturasını sürükleyin veya seçin"}
                      </p>
                    </div>
                  </div>

                  <button 
                    type="submit" 
                    disabled={reconLoading}
                    className={`w-full py-4 rounded-2xl font-bold text-sm text-white shadow-lg transition-all flex items-center justify-center gap-2 ${
                      reconLoading 
                        ? 'bg-slate-400 cursor-not-allowed shadow-none' 
                        : 'bg-gradient-to-r from-rose-500 to-rose-600 hover:from-rose-600 hover:to-rose-700 shadow-rose-100 dark:shadow-none hover:scale-[1.01] cursor-pointer'
                    }`}
                  >
                    {reconLoading ? (
                      <span className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    ) : (
                      <Activity className="w-5 h-5" />
                    )}
                    Mutabakat Analizini Çalıştır
                  </button>
                </form>
              </div>

              {/* RIGHT RESULTS COLUMN */}
              <div className="w-full lg:w-2/3 bg-white dark:bg-slate-900 rounded-2xl p-6 shadow-sm border border-slate-200 dark:border-slate-800 min-h-[500px]">
                {reconError && (
                  <div className="mb-6 p-4 bg-rose-50 dark:bg-rose-950/20 border border-rose-100 dark:border-rose-900/50 rounded-2xl text-rose-700 dark:text-rose-400 text-sm font-semibold flex items-center gap-3 animate-fadeIn">
                    <AlertCircle className="w-5 h-5 shrink-0" />
                    {reconError}
                  </div>
                )}

                {reconLoading && (
                  <div className="space-y-6 py-8 animate-pulse">
                    <div className="h-8 bg-slate-100 dark:bg-slate-800 rounded-lg w-1/3" />
                    <div className="space-y-3">
                      <div className="h-12 bg-slate-100 dark:bg-slate-800 rounded-xl" />
                      <div className="h-12 bg-slate-100 dark:bg-slate-800 rounded-xl" />
                      <div className="h-12 bg-slate-100 dark:bg-slate-800 rounded-xl" />
                      <div className="h-12 bg-slate-100 dark:bg-slate-800 rounded-xl" />
                    </div>
                  </div>
                )}

                {!reconResults && !reconLoading && (
                  <div className="h-full flex flex-col items-center justify-center text-center py-20 text-slate-400">
                    <Search className="w-16 h-16 mb-4 text-slate-300 dark:text-slate-800" />
                    <h3 className="text-lg font-bold text-slate-700 dark:text-slate-300 mb-2">Analize Hazır</h3>
                    <p className="text-sm text-slate-500 dark:text-slate-500 max-w-md leading-relaxed">
                      Sol panelden test SQL Server ve firma detaylarını girip ürettiğiniz XML faturasını yükleyerek mutabakat analizini başlatabilirsiniz.
                    </p>
                  </div>
                )}

                {reconResults && (
                  <div className="space-y-6 animate-fadeIn">
                    {/* Header Info Panel */}
                    <div className="flex flex-wrap justify-between items-center bg-slate-50 dark:bg-slate-950 border border-slate-100 dark:border-slate-800 p-4 rounded-2xl gap-3">
                      <div>
                        <p className="text-xs font-bold text-slate-400 uppercase tracking-wider">Analiz Edilen Belge</p>
                        <p className="text-lg font-bold text-slate-800 dark:text-white font-mono">{reconResults.invoice_no || "Bilinmeyen No"}</p>
                      </div>
                      
                      {reconResults.is_mock && (
                        <div className="flex items-center gap-2 px-4 py-2 bg-blue-50 dark:bg-blue-950/30 text-blue-700 dark:text-blue-300 border border-blue-100 dark:border-blue-900/50 rounded-xl text-xs font-bold animate-pulse">
                          <Activity className="w-4 h-4 shrink-0 text-blue-500" />
                          Simülasyon Modu (SQL Server Bağlantısı Fallback)
                        </div>
                      )}
                    </div>

                    {/* Comparative Table */}
                    <div className="overflow-x-auto border border-slate-100 dark:border-slate-800 rounded-2xl">
                      <table className="w-full text-left border-collapse">
                        <thead>
                          <tr className="bg-slate-50 dark:bg-slate-950 border-b border-slate-100 dark:border-slate-800">
                            <th className="p-4 text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">Kapsam</th>
                            <th className="p-4 text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">Veri Alanı</th>
                            <th className="p-4 text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">SQL Veritabanı Değeri</th>
                            <th className="p-4 text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">XML Fatura Değeri</th>
                            <th className="p-4 text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 text-center">Durum</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                          {(reconResults.audit_results || []).map((res, idx) => {
                            let statusBadge = null;
                            if (res.status === 'match') {
                              statusBadge = <span className="inline-flex px-3 py-1 rounded-full text-xs font-bold bg-emerald-50 dark:bg-emerald-950/20 text-emerald-700 dark:text-emerald-400 border border-emerald-100 dark:border-emerald-900/30">Eşleşti</span>;
                            } else if (res.status === 'mismatch') {
                              statusBadge = <span className="inline-flex px-3 py-1 rounded-full text-xs font-bold bg-rose-50 dark:bg-rose-950/20 text-rose-700 dark:text-rose-400 border border-rose-100 dark:border-rose-900/30">Uyuşmazlık</span>;
                            } else if (res.status === 'drift') {
                              statusBadge = <span className="inline-flex px-3 py-1 rounded-full text-xs font-bold bg-amber-50 dark:bg-amber-950/20 text-amber-700 dark:text-amber-400 border border-amber-100 dark:border-amber-900/30">Hassasiyet Kaybı</span>;
                            } else if (res.status === 'missing_in_db') {
                              statusBadge = <span className="inline-flex px-3 py-1 rounded-full text-xs font-bold bg-violet-50 dark:bg-violet-950/20 text-violet-700 dark:text-violet-400 border border-violet-100 dark:border-violet-900/30">DB'de Yok</span>;
                            }

                            return (
                              <tr key={idx} className="hover:bg-slate-50/50 dark:hover:bg-slate-900/30 transition-colors">
                                <td className="p-4 text-sm font-bold text-slate-700 dark:text-slate-300">{res.scope}</td>
                                <td className="p-4 text-sm text-slate-600 dark:text-slate-400">{res.field}</td>
                                <td className="p-4 text-sm font-mono text-slate-800 dark:text-slate-200">{res.db_val}</td>
                                <td className="p-4 text-sm font-mono text-slate-800 dark:text-slate-200">{res.xml_val}</td>
                                <td className="p-4 text-center">{statusBadge}</td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Premium Notification Modal */}
      {modalConfig.isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-sm transition-all duration-300 animate-fadeIn">
          <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-5 transform transition-all duration-300 scale-100 relative overflow-hidden animate-scaleIn">
            {/* Top accent line */}
            <div className={`absolute top-0 left-0 right-0 h-1.5 ${modalConfig.type === 'success' ? 'bg-emerald-500' : 'bg-rose-500'}`} />
            
            <div className="flex flex-col items-center text-center space-y-4 pt-2">
              {modalConfig.type === 'success' ? (
                <div className="w-16 h-16 bg-emerald-50 dark:bg-emerald-950/30 text-emerald-500 rounded-full flex items-center justify-center animate-bounce shadow-inner">
                  <CheckCircle2 className="w-10 h-10" />
                </div>
              ) : (
                <div className="w-16 h-16 bg-rose-50 dark:bg-rose-950/30 text-rose-500 rounded-full flex items-center justify-center animate-bounce shadow-inner">
                  <AlertCircle className="w-10 h-10" />
                </div>
              )}
              
              <h3 className="text-xl font-bold text-slate-900 dark:text-white">
                {modalConfig.title}
              </h3>
              <p className="text-sm text-slate-500 dark:text-slate-400 whitespace-pre-wrap leading-relaxed">
                {modalConfig.message}
              </p>
            </div>
            
            <button 
              onClick={() => setModalConfig(prev => ({ ...prev, isOpen: false }))}
              className={`w-full py-3 rounded-xl font-bold text-sm transition-all shadow-sm ${
                modalConfig.type === 'success' 
                  ? 'bg-emerald-600 text-white hover:bg-emerald-700 shadow-emerald-200 dark:shadow-none' 
                  : 'bg-rose-600 text-white hover:bg-rose-700 shadow-rose-200 dark:shadow-none'
              }`}
            >
              Kapat
            </button>
          </div>
        </div>
      )}

      {/* Code Diff Visual Modal */}
      {diffModal.isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/75 backdrop-blur-sm transition-all duration-300 animate-fadeIn">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-6xl w-full h-[85vh] shadow-2xl flex flex-col overflow-hidden animate-scaleIn relative">
            {/* Modal Header */}
            <div className="bg-slate-950 p-4 border-b border-slate-800 flex justify-between items-center select-none shrink-0">
              <div className="flex items-center gap-2">
                <FileCode className="w-5 h-5 text-indigo-500" />
                <h3 className="text-lg font-bold text-white font-mono break-all max-w-[150px] sm:max-w-md md:max-w-xl lg:max-w-2xl truncate">
                  {diffModal.fileName}
                </h3>
                <span className="text-xs px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 font-semibold hidden sm:inline">
                  Görsel Kod Diff
                </span>
              </div>
              
              <div className="flex items-center gap-4">
                {/* Show Only Changes Toggle */}
                <label className="flex items-center gap-2 text-xs font-bold text-slate-300 select-none cursor-pointer hover:text-white transition-colors bg-slate-850/40 px-3 py-1.5 rounded-xl border border-slate-800">
                  <input 
                    type="checkbox" 
                    checked={diffModal.showOnlyChanges}
                    onChange={(e) => setDiffModal(prev => ({ ...prev, showOnlyChanges: e.target.checked }))}
                    className="w-4 h-4 text-indigo-600 border-slate-700 bg-slate-800 rounded focus:ring-indigo-500 cursor-pointer"
                  />
                  <span>Sadece Değişiklikleri Göster (Hunk View)</span>
                </label>

                <button 
                  onClick={() => setDiffModal(prev => ({ ...prev, isOpen: false }))}
                  className="p-1.5 hover:bg-slate-800 rounded-lg text-slate-400 hover:text-white transition-colors cursor-pointer"
                >
                  <XCircle className="w-6 h-6" />
                </button>
              </div>
            </div>

            {/* Modal Content */}
            <div className="flex-1 overflow-y-auto p-6 bg-slate-950 flex flex-col">
              {diffModal.loading ? (
                <div className="flex-1 flex flex-col items-center justify-center text-slate-400">
                  <div className="w-12 h-12 border-4 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin mb-4" />
                  <p className="font-semibold text-sm">Görsel kod farklılıkları hesaplanıyor...</p>
                </div>
              ) : diffModal.error ? (
                <div className="flex-1 flex flex-col items-center justify-center text-center max-w-md mx-auto space-y-4">
                  <AlertCircle className="w-16 h-16 text-rose-500" />
                  <h4 className="text-lg font-bold text-white">Fark Gösterilemedi</h4>
                  <p className="text-sm text-slate-400">{diffModal.error}</p>
                  <button 
                    onClick={() => handleViewCodeDiff(diffModal.fileName)}
                    className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-semibold transition"
                  >
                    Tekrar Dene
                  </button>
                </div>
              ) : (
                <div className="flex-1 flex flex-col min-h-0">
                  {/* Info alert */}
                  <div className="mb-4 p-3 bg-indigo-950/40 border border-indigo-900/50 rounded-xl text-xs text-indigo-300 flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-indigo-400 shrink-0" />
                    <span>Bu analiz <b>100% yerel</b> ve <b>ücretsiz</b> gerçekleştirilmiştir. Gemini yapay zeka limitlerinizi tüketmez.</span>
                  </div>

                  {/* Diff Viewer Panel */}
                  <div className="flex-1 overflow-auto rounded-xl border border-slate-800 bg-slate-950/70 font-mono text-xs select-text">
                    <div className="min-w-[700px] divide-y divide-slate-900">
                      {getVisibleDiffLines(diffModal.diffLines, diffModal.showOnlyChanges).map((line, idx) => {
                        if (line.type === 'separator') {
                          return (
                            <div key={idx} className="flex bg-slate-900/40 text-slate-500 font-semibold select-none py-1.5 border-y border-slate-900/80 text-center justify-center italic text-[11px] leading-5">
                              {line.text}
                            </div>
                          );
                        }

                        let rowBg = '';
                        let textClass = 'text-slate-300';
                        let prefix = ' ';
                        if (line.type === 'added') {
                          rowBg = 'bg-emerald-950/30 hover:bg-emerald-950/40';
                          textClass = 'text-emerald-400 font-medium';
                          prefix = '+';
                        } else if (line.type === 'removed') {
                          rowBg = 'bg-rose-950/30 hover:bg-rose-950/40';
                          textClass = 'text-rose-400 font-medium';
                          prefix = '-';
                        } else {
                          rowBg = 'hover:bg-slate-900/30';
                        }

                        return (
                          <div key={idx} className={`flex items-stretch leading-5 ${rowBg}`}>
                            {/* Old Line Number */}
                            <div className="w-12 text-slate-600 text-right pr-3 select-none py-0.5 border-r border-slate-900 bg-slate-950/50">
                              {line.old_line || ''}
                            </div>
                            {/* New Line Number */}
                            <div className="w-12 text-slate-600 text-right pr-3 select-none py-0.5 border-r border-slate-900 bg-slate-950/50">
                              {line.new_line || ''}
                            </div>
                            {/* Diff prefix */}
                            <div className={`w-6 text-center select-none py-0.5 ${line.type === 'added' ? 'text-emerald-500' : line.type === 'removed' ? 'text-rose-500' : 'text-slate-700'}`}>
                              {prefix}
                            </div>
                            {/* Line Content */}
                            <div className={`flex-1 pl-2 whitespace-pre overflow-x-auto py-0.5 ${textClass}`}>
                              {line.text}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="bg-slate-950 p-4 border-t border-slate-800 flex justify-end items-center shrink-0">
              <button 
                onClick={() => setDiffModal(prev => ({ ...prev, isOpen: false }))}
                className="px-5 py-2.5 bg-slate-800 text-white rounded-xl text-sm font-semibold hover:bg-slate-700 transition cursor-pointer"
              >
                Kapat
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );

}

const getVisibleDiffLines = (lines, showOnlyChanges) => {
  if (!showOnlyChanges) return lines;
  
  const n = lines.length;
  const visibleIndices = new Set();
  const CONTEXT_SIZE = 3;
  
  for (let i = 0; i < n; i++) {
    if (lines[i].type === 'added' || lines[i].type === 'removed') {
      const start = Math.max(0, i - CONTEXT_SIZE);
      const end = Math.min(n - 1, i + CONTEXT_SIZE);
      for (let j = start; j <= end; j++) {
        visibleIndices.add(j);
      }
    }
  }
  
  const result = [];
  let lastIdx = -1;
  
  for (let i = 0; i < n; i++) {
    if (visibleIndices.has(i)) {
      if (lastIdx !== -1 && i - lastIdx > 1) {
        result.push({
          type: 'separator',
          text: `@@ ... ${i - lastIdx - 1} satır atlandı ... @@`
        });
      }
      result.push(lines[i]);
      lastIdx = i;
    }
  }
  
  return result;
};

export default App;

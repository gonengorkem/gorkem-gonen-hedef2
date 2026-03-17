import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Upload, FileArchive, CheckCircle2, AlertCircle, XCircle, ChevronDown, ChevronRight, Activity, Cpu, Download, MessageSquare, Send, BookOpen, Sun, Moon, Edit2, FileCode, Code2 } from 'lucide-react';

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

  const [activeTab, setActiveTab] = useState('diff'); // 'diff', 'scenarios' or 'chat'
  const [activeMainTab, setActiveMainTab] = useState('analyzer');
  const [chatMessages, setChatMessages] = useState([{role: 'bot', text: 'Merhaba! GİB kılavuzları ve e-Dönüşüm kuralları hakkında bana her şeyi sorabilirsin.'}]);
  const [chatLoading, setChatLoading] = useState(false);
  const [pdfUploadLoading, setPdfUploadLoading] = useState(false);
  const [pdfFile, setPdfFile] = useState(null);
  
  const [geminiKey, setGeminiKey] = useState('');
  const [keyLoading, setKeyLoading] = useState(false);
  const [isApiKeySaved, setIsApiKeySaved] = useState(false);
  const [darkMode, setDarkMode] = useState(false);

  useEffect(() => {
    axios.get('http://localhost:8000/api/settings/apikey/status')
      .then(res => setIsApiKeySaved(res.data.hasKey))
      .catch(err => console.error(err));
      
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
       setDarkMode(true);
    }
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

  const handleAnalyze = async () => {
    if (!oldFile || !newFile) {
      setError("Lütfen her iki (eski ve yeni) ZIP paketini de yükleyiniz.");
      return;
    }

    setLoading(true);
    setError(null);
    setResults(null);

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

  const handleSchematronValidate = async () => {
    if (!schXmlFile || !schSchFile) {
      setSchError("Lütfen hem XML hem de .sch dosyasını yükleyiniz.");
      return;
    }
    setSchLoading(true);
    setSchError(null);
    setSchResults(null);
    const formData = new FormData();
    formData.append('xml_file', schXmlFile);
    formData.append('sch_file', schSchFile);

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

  const handlePdfChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      setPdfFile(e.target.files[0]);
    }
  };

  const handleIngestPdf = async () => {
    if (!pdfFile) return;
    setPdfUploadLoading(true);
    const formData = new FormData();
    formData.append('file', pdfFile);
    try {
      const resp = await axios.post('http://localhost:8000/api/rag/ingest', formData);
      alert(resp.data.message);
      setPdfFile(null);
    } catch (err) {
      alert(err.response?.data?.detail || "Kılavuz yüklenirken bir hata oluştu.");
    } finally {
      setPdfUploadLoading(false);
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
      setChatMessages(prev => [...prev, {role: 'bot', text: "Hata: Sunucuya bağlanılamadı veya hatalı API Key. Lütfen backend .env dosyanızı kontrol ediniz."}]);
    } finally {
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
      alert(resp.data.message);
      setIsApiKeySaved(true);
      setGeminiKey('');
    } catch (err) {
      alert("Hata: " + (err.response?.data?.detail || "API Key kaydedilemedi."));
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
            onClick={() => setActiveMainTab('assistant')} 
            className={`py-4 px-6 font-bold text-sm border-b-2 transition flex items-center gap-2 ${activeMainTab === 'assistant' ? 'border-blue-600 text-blue-700 bg-blue-50/50' : 'border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:text-slate-200 hover:bg-slate-50 dark:bg-slate-950'}`}>
            <MessageSquare className="w-5 h-5"/> Akıllı GİB Asistanı
          </button>
        </div>
      </div>

      <main className="max-w-6xl mx-auto py-8 px-4">
        
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
                   className={`px-6 py-3 font-semibold text-sm rounded-t-lg transition border-b-2 ${activeTab === 'diff' ? 'bg-white dark:bg-slate-900 border-indigo-600 text-indigo-700' : 'border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:text-slate-200'}`}>
                   Fark Görüntüleyici (Diff)
                 </button>
                 <button 
                   onClick={() => setActiveTab('scenarios')}
                   className={`px-6 py-3 font-semibold text-sm rounded-t-lg transition border-b-2 flex items-center gap-2 ${activeTab === 'scenarios' ? 'bg-white dark:bg-slate-900 border-emerald-500 text-emerald-700' : 'border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:text-slate-200'}`}>
                   Otomatik Test Senaryoları
                   <span className="bg-emerald-100 text-emerald-700 py-0.5 px-2 rounded-full text-xs font-bold">{results.scenarios.length} Senaryo</span>
                 </button>
                 {/* Assistant moved to main tabs */}
               </div>
               
               {activeTab === 'scenarios' && (
                 <button 
                   onClick={exportScenariosToCSV} 
                   className="mb-2 mr-4 px-4 py-2 bg-slate-800 text-white text-sm font-semibold rounded-lg hover:bg-slate-900 transition flex items-center gap-2 shadow-sm">
                   <Download className="w-4 h-4" /> Senaryoları İndir (CSV/Excel)
                 </button>
               )}
            </div>

            {/* CONTENT TABS */}
            <div className="bg-white dark:bg-slate-900 rounded-2xl rounded-tl-none shadow-sm border border-slate-200 dark:border-slate-800 overflow-hidden min-h-[500px]">
               
               {activeTab === 'diff' && (
                 <div className="p-6">
                    {results.diff_results.filter(f => f.status !== 'unchanged').length === 0 ? (
                      <div className="text-center py-20 text-slate-500 dark:text-slate-400">
                         <CheckCircle2 className="w-16 h-16 mx-auto mb-4 text-slate-300" />
                         <p className="text-lg font-medium">Paketler arasında herhangi bir farklılık bulunamadı.</p>
                      </div>
                    ) : (
                      <div className="space-y-6">
                         {results.diff_results.filter(f => f.status !== 'unchanged').map((file, idx) => (
                           <div key={idx} className="border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden bg-slate-50 dark:bg-slate-950 shadow-sm">
                              <div className="bg-slate-100 dark:bg-slate-800 p-4 font-mono text-sm font-semibold border-b border-slate-200 dark:border-slate-800 flex justify-between items-center text-slate-700 dark:text-slate-300">
                                <span>{file.file}</span>
                                <span className={`text-xs px-2 py-1 rounded-md uppercase font-bold shadow-sm border
                                  ${file.status === 'new_file' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 
                                  file.status === 'deleted_file' ? 'bg-red-50 text-red-700 border-red-200' : 'bg-amber-50 text-amber-700 border-amber-200'}
                                `}>
                                  {file.status === 'new_file' ? 'YENİ EKLENDİ' : file.status === 'deleted_file' ? 'SİLİNDİ' : 'DEĞİŞTİRİLDİ'}
                                </span>
                              </div>
                              <div className="p-5 space-y-4 bg-white dark:bg-slate-900">
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
                                      <p className="text-slate-700 dark:text-slate-300 ml-4 font-medium">{diffItem.message}</p>
                                      
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
                           </div>
                         ))}
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
                        <tbody className="divide-y divide-slate-100">
                           {results.scenarios.map((scen, idx) => (
                             <tr key={idx} className="hover:bg-slate-50 dark:bg-slate-950 transition-colors">
                               <td className="p-4 align-top">
                                 <p className="font-semibold text-slate-800 dark:text-slate-200 break-all">{scen.target}</p>
                                 <p className="text-xs text-slate-400 mt-1 break-all">{scen.file}</p>
                               </td>
                               <td className="p-4 align-top">
                                 <span className="inline-block px-2 py-1 bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 rounded-md text-xs font-bold whitespace-nowrap">
                                   {scen.type}
                                 </span>
                               </td>
                               <td className="p-4 align-top text-emerald-900 leading-relaxed bg-emerald-50/30">
                                 <div className="flex gap-2">
                                   <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0" />
                                   <p>{scen.positive}</p>
                                 </div>
                               </td>
                               <td className="p-4 align-top text-red-900 leading-relaxed bg-red-50/30">
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
                <div className="relative border-2 border-dashed border-slate-300 dark:border-slate-700 rounded-xl p-8 text-center hover:bg-slate-50 dark:bg-slate-950 hover:border-emerald-400 transition-colors cursor-pointer" onClick={() => document.getElementById('sch-sch-file').click()}>
                  <input id="sch-sch-file" type="file" accept=".sch" className="hidden" onChange={(e) => handleSchFileChange(e, 'sch')} />
                  <Code2 className={`w-12 h-12 mx-auto mb-3 ${schSchFile ? 'text-emerald-600' : 'text-slate-400'}`} />
                  {schSchFile ? (
                    <div>
                      <p className="font-semibold text-emerald-700">{schSchFile.name}</p>
                      <p className="text-xs text-slate-500 dark:text-slate-400">{(schSchFile.size / 1024).toFixed(2)} KB</p>
                    </div>
                  ) : (
                    <p className="text-slate-500 dark:text-slate-400 text-sm">Şematron (.sch) dosyasını seçin.</p>
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
              disabled={schLoading || !schXmlFile || !schSchFile}
              className={`w-full py-4 rounded-xl flex items-center justify-center gap-2 font-bold text-lg transition-all ${
                schLoading || !schXmlFile || !schSchFile 
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
                        <div className="mt-2 text-xs text-slate-500 font-mono bg-slate-100 dark:bg-slate-800 p-2 rounded break-all">
                          <div><strong>Konum (Location):</strong> {errItem.location}</div>
                          <div className="mt-1"><strong>Kural (Test):</strong> {errItem.test}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
            
          </div>
        </div>

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

                   <div className="mt-8 p-4 bg-blue-50 border border-blue-100 rounded-xl text-xs text-blue-800 leading-relaxed max-h-48 overflow-auto">
                      <strong>Bilgi:</strong> Akıllı GİB Asistanı, kendi hafızasını (Vektör DB) kullanır. Sorularınızı yanıtlarken en son yüklediğiniz <b>Kılavuzlara</b> dayanarak %100 doğrulukla ve halüsinasyon yapmadan cevap vermeye çalışır.
                   </div>
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
                               <div style={{whiteSpace: 'pre-wrap', lineHeight: '1.6'}}>{msg.text}</div>
                            </div>
                         </div>
                      ))}
                      {chatLoading && (
                         <div className="flex justify-start">
                            <div className="bg-white dark:bg-slate-900 text-slate-500 dark:text-slate-400 rounded-2xl rounded-bl-none p-4 text-sm max-w-[80%] border border-slate-200 dark:border-slate-800 flex items-center gap-2 shadow-sm">
                               <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce"></div>
                               <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
                               <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{animationDelay: '0.4s'}}></div>
                            </div>
                         </div>
                      )}
                   </div>
                   
                   <ChatInputBox onSend={handleSendChat} loading={chatLoading} />
                </div>
             </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;

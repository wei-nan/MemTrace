import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { 
  Network, 
  PlusCircle, 
  Search, 
  Settings, 
  Save, 
  BrainCircuit,
  Tag as TagIcon,
  X,
  Globe
} from 'lucide-react';
import './index.css';

function App() {
  const { t, i18n } = useTranslation();
  const [activeTab, setActiveTab] = useState<'zh' | 'en'>('zh');
  const [tags, setTags] = useState<string[]>(['knowledge', 'system']);
  const [currentTag, setCurrentTag] = useState('');

  const handleAddTag = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && currentTag.trim() && !tags.includes(currentTag.trim())) {
      e.preventDefault();
      setTags([...tags, currentTag.trim()]);
      setCurrentTag('');
    }
  };

  const removeTag = (tagToRemove: string) => {
    setTags(tags.filter(tag => tag !== tagToRemove));
  };

  const toggleUiLang = () => {
    i18n.changeLanguage(i18n.language === 'zh-TW' ? 'en' : 'zh-TW');
  };

  return (
    <div className="app-container">
      {/* Sidebar Layout */}
      <aside className="sidebar">
        <div className="brand" style={{ justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div className="brand-icon">
              <BrainCircuit size={20} />
            </div>
            <div className="brand-text">MemTrace</div>
          </div>
          <button 
            className="btn-secondary" 
            style={{ padding: '6px 10px', display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem' }}
            onClick={toggleUiLang}
            title="Toggle Language"
          >
            <Globe size={14} />
            {i18n.language === 'zh-TW' ? 'EN' : '中文'}
          </button>
        </div>

        <nav>
          <div className="nav-item active">
            <PlusCircle size={18} />
            {t('sidebar.write')}
          </div>
          <div className="nav-item">
            <Network size={18} />
            {t('sidebar.graph')}
          </div>
          <div className="nav-item">
            <Search size={18} />
            {t('sidebar.explore')}
          </div>
        </nav>

        <div style={{ marginTop: 'auto' }}>
          <div className="nav-item">
            <Settings size={18} />
            {t('sidebar.settings')}
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="main-content">
        <header className="page-header animate-fade-in">
          <h1 className="page-title">{t('header.title')}</h1>
          <p className="page-subtitle">{t('header.subtitle')}</p>
        </header>

        <form className="glass-panel animate-fade-in" style={{ padding: '32px', animationDelay: '0.1s' }} onSubmit={(e) => e.preventDefault()}>
          <div className="tabs">
            <div 
              className={`tab ${activeTab === 'zh' ? 'active' : ''}`}
              onClick={() => setActiveTab('zh')}
            >
              {t('form.tab_zh')}
            </div>
            <div 
              className={`tab ${activeTab === 'en' ? 'active' : ''}`}
              onClick={() => setActiveTab('en')}
            >
              {t('form.tab_en')}
            </div>
          </div>

          <div className="editor-grid">
            <div className="form-group two-col">
              <label className="form-label">{t('form.title')}</label>
              <input 
                type="text" 
                className="form-input" 
                placeholder={t('form.titleP')}
              />
            </div>

            <div className="form-group">
              <label className="form-label">{t('form.type')}</label>
              <select className="form-select">
                <option value="factual">{t('form.type_factual')}</option>
                <option value="procedural">{t('form.type_procedural')}</option>
                <option value="preference">{t('form.type_preference')}</option>
                <option value="context">{t('form.type_context')}</option>
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">{t('form.vis')}</label>
              <select className="form-select">
                <option value="private">{t('form.vis_private')}</option>
                <option value="team">{t('form.vis_team')}</option>
                <option value="public">{t('form.vis_public')}</option>
              </select>
            </div>

            <div className="form-group two-col">
              <label className="form-label">{t('form.body')}</label>
              <textarea 
                className="form-textarea" 
                placeholder={t('form.bodyP')}
              ></textarea>
            </div>

            <div className="form-group two-col">
              <label className="form-label">{t('form.tags')}</label>
              <div style={{ position: 'relative' }}>
                <TagIcon size={16} color="var(--text-muted)" style={{ position: 'absolute', left: '12px', top: '14px' }} />
                <input 
                  type="text" 
                  className="form-input" 
                  style={{ paddingLeft: '36px' }}
                  placeholder={t('form.tagsP')}
                  value={currentTag}
                  onChange={(e) => setCurrentTag(e.target.value)}
                  onKeyDown={handleAddTag}
                />
              </div>
              <div className="tag-container">
                {tags.map(tag => (
                  <span className="tag" key={tag}>
                    #{tag}
                    <X size={12} className="tag-remove" onClick={() => removeTag(tag)} />
                  </span>
                ))}
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '32px', paddingTop: '24px', borderTop: '1px solid var(--panel-border)' }}>
            <button type="button" className="btn-secondary">{t('form.saveDraft')}</button>
            <button type="submit" className="btn-primary">
              <Save size={18} />
              {t('form.commit')}
            </button>
          </div>
        </form>
      </main>
    </div>
  );
}

export default App;

import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

const resources = {
  'zh-TW': {
    translation: {
      sidebar: {
        write: '撰寫記憶',
        graph: '知識圖譜',
        explore: '探索 Hub',
        settings: '設定'
      },
      header: {
        title: '捕捉知識',
        subtitle: '在您的本地圖譜中建立一個新的記憶節點。'
      },
      form: {
        tab_zh: '繁體中文 (zh-TW)',
        tab_en: '英文 (en)',
        title: '記憶標題',
        titleP: '為這個記憶下一個精準的標題...',
        type: '內容類型',
        type_factual: '事實 (Facts, specs, data)',
        type_procedural: '程序 (How-tos, steps)',
        type_preference: '偏好 (Choices, favorites)',
        type_context: '背景 (Background, history)',
        vis: '可見度',
        vis_private: '私人 (Private)',
        vis_team: '團隊 (Team)',
        vis_public: '公開 (Public)',
        body: '記憶內容',
        bodyP: '在這裡留下詳細的知識紀錄...',
        tags: '語義標籤',
        tagsP: '輸入標籤後按下 Enter...',
        saveDraft: '儲存草稿',
        commit: '提交記憶',
        exportLocal: '匯出 JSON',
        importLocal: '匯入 JSON',
        importMarkdown: '匯入 Markdown'
      }
    }
  },
  en: {
    translation: {
      sidebar: {
        write: 'Write Memory',
        graph: 'Knowledge Graph',
        explore: 'Explore Hub',
        settings: 'Settings'
      },
      header: {
        title: 'Capture Knowledge',
        subtitle: 'Create a new memory node in your local knowledge graph.'
      },
      form: {
        tab_zh: 'Traditional Chinese (zh-TW)',
        tab_en: 'English (en)',
        title: 'Memory Title',
        titleP: 'Give this memory a precise title...',
        type: 'Content Type',
        type_factual: 'Factual (Facts, specs, data)',
        type_procedural: 'Procedural (How-tos, steps)',
        type_preference: 'Preference (Choices, favorites)',
        type_context: 'Context (Background, history)',
        vis: 'Visibility',
        vis_private: 'Private (Only me)',
        vis_team: 'Team (Organization space)',
        vis_public: 'Public (Global hub)',
        body: 'Memory Body',
        bodyP: 'Record the detailed knowledge here...',
        tags: 'Semantic Tags',
        tagsP: 'Type a tag and press Enter...',
        saveDraft: 'Save as Draft',
        commit: 'Commit Memory',
        exportLocal: 'Export JSON',
        importLocal: 'Import JSON',
        importMarkdown: 'Import Markdown'
      }
    }
  }
};

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    fallbackLng: 'zh-TW',
    interpolation: {
      escapeValue: false,
    }
  });

export default i18n;

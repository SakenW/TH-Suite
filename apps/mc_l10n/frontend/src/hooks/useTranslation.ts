import { useTranslation as useI18nTranslation } from 'react-i18next';

/**
 * Custom hook for translations with type safety
 */
export const useTranslation = (namespace?: string) => {
  const { t, i18n } = useI18nTranslation(namespace);

  return {
    t,
    i18n,
    changeLanguage: i18n.changeLanguage,
    currentLanguage: i18n.language,
    isLoading: !i18n.isInitialized,
  };
};

/**
 * Hook specifically for common translations
 */
export const useCommonTranslation = () => {
  return useTranslation('common');
};

/**
 * Hook specifically for MC Studio translations
 */
export const useMcStudioTranslation = () => {
  return useTranslation('mcStudio');
};
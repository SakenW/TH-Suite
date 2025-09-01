/**
 * 搜索框组件
 * 功能丰富的搜索组件，支持自动完成、历史记录、过滤器等
 */

import React, { useState, useRef, useCallback, useEffect } from 'react';
import {
  TextField,
  InputAdornment,
  IconButton,
  Paper,
  Popper,
  ClickAwayListener,
  MenuList,
  MenuItem,
  ListItemIcon,
  ListItemText,
  Divider,
  Typography,
  Box,
  Chip,
  Fade,
  CircularProgress,
} from '@mui/material';
import { useTheme, alpha } from '@mui/material/styles';
import {
  Search,
  X,
  Clock,
  Filter,
  TrendingUp,
  Star,
  Tag,
  ArrowUpRight,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface SearchSuggestion {
  id: string;
  text: string;
  type: 'recent' | 'popular' | 'suggestion' | 'filter' | 'tag';
  count?: number;
  icon?: React.ReactNode;
  category?: string;
}

interface SearchBoxProps {
  placeholder?: string;
  value?: string;
  onChange?: (value: string) => void;
  onSearch?: (query: string) => void;
  onClear?: () => void;
  
  // 自动完成功能
  suggestions?: SearchSuggestion[];
  showSuggestions?: boolean;
  loading?: boolean;
  onSuggestionSelect?: (suggestion: SearchSuggestion) => void;
  
  // 搜索历史
  recentSearches?: string[];
  maxRecentSearches?: number;
  onRecentSearchClick?: (search: string) => void;
  
  // 热门搜索
  popularSearches?: string[];
  onPopularSearchClick?: (search: string) => void;
  
  // 过滤器标签
  activeFilters?: Array<{ label: string; value: string; color?: string }>;
  onFilterRemove?: (value: string) => void;
  
  // 样式配置
  size?: 'small' | 'medium' | 'large';
  variant?: 'outlined' | 'filled' | 'standard';
  fullWidth?: boolean;
  debounceMs?: number;
  
  // 快捷键支持
  shortcutKey?: string; // 例如 "Ctrl+K"
}

export const SearchBox: React.FC<SearchBoxProps> = ({
  placeholder = '搜索...',
  value = '',
  onChange,
  onSearch,
  onClear,
  suggestions = [],
  showSuggestions = true,
  loading = false,
  onSuggestionSelect,
  recentSearches = [],
  maxRecentSearches = 5,
  onRecentSearchClick,
  popularSearches = [],
  onPopularSearchClick,
  activeFilters = [],
  onFilterRemove,
  size = 'medium',
  variant = 'outlined',
  fullWidth = false,
  debounceMs = 300,
  shortcutKey,
}) => {
  const theme = useTheme();
  const [focused, setFocused] = useState(false);
  const [inputValue, setInputValue] = useState(value);
  const [showDropdown, setShowDropdown] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const anchorRef = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<NodeJS.Timeout>();

  // 同步外部 value 变化
  useEffect(() => {
    setInputValue(value);
  }, [value]);

  // 防抖处理
  const debouncedOnChange = useCallback((newValue: string) => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }
    
    debounceRef.current = setTimeout(() => {
      if (onChange) {
        onChange(newValue);
      }
    }, debounceMs);
  }, [onChange, debounceMs]);

  // 处理输入变化
  const handleInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = event.target.value;
    setInputValue(newValue);
    debouncedOnChange(newValue);
    
    if (showSuggestions && newValue.length > 0) {
      setShowDropdown(true);
    }
  };

  // 处理搜索
  const handleSearch = () => {
    if (onSearch && inputValue.trim()) {
      onSearch(inputValue.trim());
      setShowDropdown(false);
    }
  };

  // 处理清除
  const handleClear = () => {
    setInputValue('');
    setShowDropdown(false);
    if (onChange) onChange('');
    if (onClear) onClear();
  };

  // 处理建议选择
  const handleSuggestionClick = (suggestion: SearchSuggestion) => {
    if (suggestion.type === 'filter') {
      // 过滤器类型的建议，不改变搜索框内容
      if (onSuggestionSelect) {
        onSuggestionSelect(suggestion);
      }
    } else {
      setInputValue(suggestion.text);
      if (onChange) onChange(suggestion.text);
      if (onSearch) onSearch(suggestion.text);
    }
    setShowDropdown(false);
  };

  // 处理键盘事件
  const handleKeyDown = (event: React.KeyboardEvent) => {
    switch (event.key) {
      case 'Enter':
        event.preventDefault();
        handleSearch();
        break;
      case 'Escape':
        setShowDropdown(false);
        inputRef.current?.blur();
        break;
      case 'ArrowDown':
        if (!showDropdown && inputValue.length > 0) {
          setShowDropdown(true);
        }
        break;
    }
  };

  // 快捷键支持
  useEffect(() => {
    if (shortcutKey) {
      const handleKeyDown = (event: KeyboardEvent) => {
        const keys = shortcutKey.toLowerCase().split('+');
        let match = true;
        
        if (keys.includes('ctrl') && !event.ctrlKey) match = false;
        if (keys.includes('alt') && !event.altKey) match = false;
        if (keys.includes('shift') && !event.shiftKey) match = false;
        if (keys.includes('meta') && !event.metaKey) match = false;
        
        const mainKey = keys[keys.length - 1];
        if (event.key.toLowerCase() !== mainKey) match = false;
        
        if (match) {
          event.preventDefault();
          inputRef.current?.focus();
        }
      };
      
      document.addEventListener('keydown', handleKeyDown);
      return () => document.removeEventListener('keydown', handleKeyDown);
    }
  }, [shortcutKey]);

  // 获取图标
  const getSuggestionIcon = (suggestion: SearchSuggestion) => {
    if (suggestion.icon) return suggestion.icon;
    
    switch (suggestion.type) {
      case 'recent':
        return <Clock size={16} />;
      case 'popular':
        return <TrendingUp size={16} />;
      case 'filter':
        return <Filter size={16} />;
      case 'tag':
        return <Tag size={16} />;
      default:
        return <Search size={16} />;
    }
  };

  // 构建建议列表
  const buildSuggestionList = () => {
    const items: React.ReactNode[] = [];
    
    // 搜索建议
    if (suggestions.length > 0) {
      const searchSuggestions = suggestions.filter(s => 
        s.type === 'suggestion' && 
        s.text.toLowerCase().includes(inputValue.toLowerCase())
      );
      
      if (searchSuggestions.length > 0) {
        items.push(
          <Box key="suggestions-header" sx={{ px: 2, py: 1 }}>
            <Typography variant="overline" color="text.secondary" sx={{ fontWeight: 600 }}>
              搜索建议
            </Typography>
          </Box>
        );
        
        searchSuggestions.forEach(suggestion => {
          items.push(
            <MenuItem
              key={suggestion.id}
              onClick={() => handleSuggestionClick(suggestion)}
              sx={{
                py: 1,
                '&:hover': {
                  backgroundColor: alpha(theme.palette.primary.main, 0.08),
                },
              }}
            >
              <ListItemIcon sx={{ minWidth: 36 }}>
                {getSuggestionIcon(suggestion)}
              </ListItemIcon>
              <ListItemText
                primary={suggestion.text}
                secondary={suggestion.category}
                primaryTypographyProps={{ variant: 'body2' }}
                secondaryTypographyProps={{ variant: 'caption' }}
              />
              {suggestion.count && (
                <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>
                  {suggestion.count}
                </Typography>
              )}
            </MenuItem>
          );
        });
        
        items.push(<Divider key="suggestions-divider" />);
      }
    }
    
    // 最近搜索
    if (recentSearches.length > 0 && (!inputValue || inputValue.length === 0)) {
      items.push(
        <Box key="recent-header" sx={{ px: 2, py: 1 }}>
          <Typography variant="overline" color="text.secondary" sx={{ fontWeight: 600 }}>
            最近搜索
          </Typography>
        </Box>
      );
      
      recentSearches.slice(0, maxRecentSearches).forEach((search, index) => {
        items.push(
          <MenuItem
            key={`recent-${index}`}
            onClick={() => {
              setInputValue(search);
              if (onRecentSearchClick) onRecentSearchClick(search);
              setShowDropdown(false);
            }}
            sx={{ py: 1 }}
          >
            <ListItemIcon sx={{ minWidth: 36 }}>
              <Clock size={16} />
            </ListItemIcon>
            <ListItemText
              primary={search}
              primaryTypographyProps={{ variant: 'body2' }}
            />
            <ArrowUpRight size={14} style={{ opacity: 0.5 }} />
          </MenuItem>
        );
      });
      
      if (popularSearches.length > 0) {
        items.push(<Divider key="recent-divider" />);
      }
    }
    
    // 热门搜索
    if (popularSearches.length > 0 && (!inputValue || inputValue.length === 0)) {
      items.push(
        <Box key="popular-header" sx={{ px: 2, py: 1 }}>
          <Typography variant="overline" color="text.secondary" sx={{ fontWeight: 600 }}>
            热门搜索
          </Typography>
        </Box>
      );
      
      popularSearches.slice(0, 5).forEach((search, index) => {
        items.push(
          <MenuItem
            key={`popular-${index}`}
            onClick={() => {
              setInputValue(search);
              if (onPopularSearchClick) onPopularSearchClick(search);
              setShowDropdown(false);
            }}
            sx={{ py: 1 }}
          >
            <ListItemIcon sx={{ minWidth: 36 }}>
              <TrendingUp size={16} />
            </ListItemIcon>
            <ListItemText
              primary={search}
              primaryTypographyProps={{ variant: 'body2' }}
            />
            <Star size={14} style={{ opacity: 0.5 }} />
          </MenuItem>
        );
      });
    }
    
    return items;
  };

  return (
    <Box ref={anchorRef} sx={{ position: 'relative' }}>
      {/* 活跃过滤器标签 */}
      <AnimatePresence>
        {activeFilters.length > 0 && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
          >
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 1 }}>
              {activeFilters.map((filter) => (
                <Chip
                  key={filter.value}
                  label={filter.label}
                  size="small"
                  onDelete={() => onFilterRemove?.(filter.value)}
                  sx={{
                    backgroundColor: filter.color 
                      ? alpha(filter.color, 0.1) 
                      : alpha(theme.palette.primary.main, 0.1),
                    color: filter.color || theme.palette.primary.main,
                    '& .MuiChip-deleteIcon': {
                      color: filter.color || theme.palette.primary.main,
                    },
                  }}
                />
              ))}
            </Box>
          </motion.div>
        )}
      </AnimatePresence>

      {/* 搜索输入框 */}
      <TextField
        ref={inputRef}
        value={inputValue}
        onChange={handleInputChange}
        onKeyDown={handleKeyDown}
        onFocus={() => {
          setFocused(true);
          if (showSuggestions && (inputValue.length > 0 || recentSearches.length > 0 || popularSearches.length > 0)) {
            setShowDropdown(true);
          }
        }}
        onBlur={() => setFocused(false)}
        placeholder={shortcutKey ? `${placeholder} (${shortcutKey})` : placeholder}
        variant={variant}
        size={size}
        fullWidth={fullWidth}
        InputProps={{
          startAdornment: (
            <InputAdornment position="start">
              {loading ? (
                <CircularProgress size={20} />
              ) : (
                <Search size={20} color={theme.palette.text.secondary} />
              )}
            </InputAdornment>
          ),
          endAdornment: inputValue && (
            <InputAdornment position="end">
              <IconButton
                aria-label="清除搜索"
                onClick={handleClear}
                edge="end"
                size="small"
              >
                <X size={16} />
              </IconButton>
            </InputAdornment>
          ),
          sx: {
            borderRadius: 3,
            '& .MuiOutlinedInput-root': {
              transition: 'all 0.2s ease-in-out',
              '&:hover': {
                backgroundColor: alpha(theme.palette.action.hover, 0.04),
              },
              '&.Mui-focused': {
                backgroundColor: 'background.paper',
                boxShadow: `0 0 0 2px ${alpha(theme.palette.primary.main, 0.2)}`,
              },
            },
          },
        }}
      />

      {/* 搜索建议下拉框 */}
      <Popper
        open={showDropdown}
        anchorEl={anchorRef.current}
        placement="bottom-start"
        style={{ width: anchorRef.current?.offsetWidth, zIndex: 1300 }}
        transition
      >
        {({ TransitionProps }) => (
          <Fade {...TransitionProps} timeout={200}>
            <Paper
              elevation={8}
              sx={{
                mt: 1,
                maxHeight: 400,
                overflow: 'auto',
                border: `1px solid ${alpha(theme.palette.divider, 0.2)}`,
                borderRadius: 2,
              }}
            >
              <ClickAwayListener onClickAway={() => setShowDropdown(false)}>
                <MenuList dense>
                  {buildSuggestionList()}
                  {buildSuggestionList().length === 0 && inputValue && (
                    <Box sx={{ p: 3, textAlign: 'center' }}>
                      <Typography variant="body2" color="text.secondary">
                        没有找到相关建议
                      </Typography>
                    </Box>
                  )}
                </MenuList>
              </ClickAwayListener>
            </Paper>
          </Fade>
        )}
      </Popper>
    </Box>
  );
};
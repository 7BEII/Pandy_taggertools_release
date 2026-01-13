// Alpine.js 主应用逻辑
function taggerApp() {
    return {
        // 数据状态
        notifications: [],
        notificationId: 0,
        config: {
            providers: {
                siliconflow: { api_key: '', base_url: 'https://api.siliconflow.cn/v1' },
                modelscope: { api_key: '', base_url: 'https://api-inference.modelscope.cn/v1' },
                tuzi: { api_key: '', base_url: 'https://api.tuziapi.com/v1' }
            },
            current_provider: 'siliconflow',
            model: 'Qwen/Qwen2.5-VL-72B-Instruct',
            system_prompt: '',
            user_prompt: '',
            prompt_templates: {
                tagging: { selected: 'default', templates: [] },
                editing: { selected: 'default', templates: [] }
            }
        },
        providerNames: {
            siliconflow: 'SiliconFlow (硅基流动)',
            modelscope: 'ModelScope (魔塔)',
            tuzi: 'Tuzi API'
        },
        availableModels: [
            'Qwen/Qwen2.5-VL-32B-Instruct',
            'Qwen/Qwen2.5-VL-7B-Instruct',
            'Qwen/Qwen2.5-VL-72B-Instruct',
            'Qwen/Qwen2-VL-72B-Instruct',
            'Pro/Qwen/Qwen2-VL-7B-Instruct',
            'Qwen/Qwen3-VL-8B-Instruct',
            'Qwen/Qwen3-VL-32B-Instruct'
        ],
        images: [],
        pairs: [],
        detailImage: null,
        detailPair: null,
        previewImage: null,
        isProcessing: false,
        progress: 0,
        taskStatus: {},
        currentTaskId: null,
        lastFailedIds: [],  // 上次失败的图片/组ID
        lastFailedType: '',  // 上次失败的类型: 'images' 或 'pairs'
        isImporting: false,
        importProgress: 0,
        importProgressText: '',
        
        // UI 状态
        modelMode: 'tagging',
        theme: 'light',  // 主题: 'light' 或 'dark'
        showSettingsModal: false,
        showAnalyzerSettingsModal: false,  // 训练分析器设置模态框
        showPromptTemplateManager: false,  // 提示词模板管理器
        settingsTab: 'appearance',  // 'appearance', 'apikey', 'license'
        // 激活/授权状态
        isLicensed: false,
        licenseCpuHex: '',
        licenseInput: '',
        licenseStatus: '',
        showSystemPrompt: true,
        showUserPrompt: true,
        showRenameDialog: false,
        showAddTextDialog: false,
        showResizeDialog: false,
        fullscreenImage: null,  // 全屏查看的图片URL
        fullscreenImageSide: 'left',  // 当前全屏查看的是哪一侧 'left' 或 'right'

        promptTemplateMode: 'tagging',
        newPromptTemplateName: '',
        
        // 翻译功能状态
        isTranslating: false,
        isSyncingTranslation: false,
        translatedChineseText: '',
        currentTranslatingImageId: null,
        detailTranslateLang: 'zh',  // 详情弹窗翻译目标语言: 'zh' 或 'en'
        translateProvider: 'modelscope',  // 翻译API厂商
        translateModelId: 'deepseek-ai/DeepSeek-V3-0324',  // 翻译模型ID
        showTranslateLangDropdown: false,  // 语言选择下拉框
        showTranslateModelDropdown: false,  // 模型选择下拉框
        showSentenceMapping: false,  // 是否显示句子对照模式
        originalSentences: [],  // 原文句子数组
        translatedSentences: [],  // 翻译句子数组
        initialTranslatedSentences: [],  // 翻译完成时的原始翻译句子（用于比较修改）
        modifiedSentenceFlags: [],  // 标记哪些句子被修改了（true表示被修改）
        syncingSentenceIndex: -1,  // 正在同步的句子索引
        originalDetailImageText: '',  // 原始文本（用于取消时恢复）
        originalDetailPairText: '',  // 原始文本（用于取消时恢复）
        
        // 句级编辑追踪状态
        isComposing: false,  // 是否正在使用输入法组合输入
        sentenceDataStore: [],  // 句子数据存储: [{index, originalContent, currentContent, dirty}]
        pendingNewSentences: [],  // 待同步的新增句子
        
        // 翻译专用模型配置
        translateModels: {
            modelscope: [
                { id: 'Qwen/Qwen2.5-72B-Instruct', name: 'Qwen2.5-72B' }
            ],
            siliconflow: [
                { id: 'Qwen/Qwen2.5-72B-Instruct', name: 'Qwen2.5-72B' }
            ],
            tuzi: [
                { id: 'gpt-4o', name: 'GPT-4o' },
                { id: 'chatgpt-4o-latest', name: 'ChatGPT-4o-Latest' },
                { id: 'gpt-4o-mini', name: 'GPT-4o-Mini' },
                { id: 'gpt-4-turbo', name: 'GPT-4-Turbo' },
                { id: 'gpt-3.5-turbo', name: 'GPT-3.5-Turbo' }
            ]
        },
        
        // API Key配置（独立存储）
        apikeyConfig: {
            providers: {
                siliconflow: { api_key: '', base_url: 'https://api.siliconflow.cn/v1', models: [] },
                modelscope: { api_key: '', base_url: 'https://api-inference.modelscope.cn/v1', models: [] },
                tuzi: { api_key: '', base_url: 'https://api.tu-zi.com/v1', models: [] }
            },
            current_provider: 'siliconflow',
            model: 'Qwen/Qwen2.5-VL-72B-Instruct',
            ai_analysis_prompt: ''
        },
        
        // AI分析默认系统提示词
        defaultAiAnalysisPrompt: `你是一位专业的深度学习训练分析专家。请根据提供的训练数据，分析训练过程并给出优化建议。

分析要点：
1. 训练曲线分析：Loss变化趋势、收敛情况、是否存在过拟合/欠拟合
2. 最优Epoch分析：最佳checkpoint选择建议
3. 超参数建议：学习率、batch size、训练轮数等调整建议
4. 潜在问题诊断：训练中可能存在的问题及解决方案

请用中文回答，给出具体、可操作的建议。`,
        
        // 模型管理弹窗状态
        showModelManageDialog: false,
        
        // 模型编辑弹窗状态
        showModelEditDialog: false,
        editingModelIndex: -1,  // -1表示新增，>=0表示编辑
        editingModel: { id: '', name: '' },
        
        // 模板文件列表
        templateFiles: [],
        selectedTaggingTemplate: '',
        selectedEditingTemplate: '',
        selectedTaggingTemplateId: 'default',  // 侧边栏使用的模板ID
        selectedEditingTemplateId: 'default',  // 侧边栏使用的模板ID
        
        // 导出对话框状态
        showExportDialog: false,
        showImageExportDialog: false,  // 单图导出对话框
        imageExportFormat: 'png',      // 单图导出格式
        imageExportOutputType: 'zip',  // 单图导出类型
        imageExportPath: '',           // 单图导出路径
        exportImageFormat: 'png',
        exportOutputDir: '',
        exportFileName: '',
        showExportSuccessDialog: false,
        exportedFilePath: '',
        exportedFolderPath: '',  // 导出文件夹路径（用于打开文件夹）
        // 命名规则
        exportNamingMode: 'default',  // 'default', 't2itrainer', 'aitoolkit', 'runinghub'
        exportSuffixLeft: 'R',        // 原图1后缀
        exportSuffixLeft2: 'G',       // 原图2后缀（如果有）
        exportSuffixRight: 'T',       // 目标图后缀
        exportTxtFollows: 'right',    // txt跟随: 'left' 或 'right'
        exportFolderPrefix: 'aitoolkit',  // AIToolkit模式文件夹前缀
        exportUnifiedFilePrefix: 'T', // AIToolkit模式统一文件前缀
        exportTxtFolderFollows: 'right',  // txt放置文件夹跟随: 'left' 或 'right'
        exportRuninghubStart: 'start',  // RuningHub模式原图后缀
        exportRuninghubEnd: 'end',    // RuningHub模式目标图后缀
        exportOutputType: 'zip',      // 导出类型: 'zip' 或 'folder'
        exportFilterKeyword: '',      // 按文件名关键字过滤（可选）
        exportFilterPNG: true,        // 导出PNG（默认勾选）
        exportFilterJPG: false,       // 导出JPG
        exportFilterTXT: true,        // 导出TXT（默认勾选）
        exportPrefixLetter: false,    // 是否前置字母（例如 R_1）
        
        // 确认对话框状态
        showConfirmDialog: false,
        confirmTitle: '',
        confirmMessage: '',
        confirmCallback: null,
        
        // 对话框输入值
        renamePrefix: 'lora_data',
        addTextValue: 'PD_style',
        resizeValue: 1024,

        // 自定义裁剪状态
        showCustomCropDialog: false,
        cropImages: [],  // 待裁剪的图片列表
        cropTargetWidth: 1024,
        cropTargetHeight: 1024,
        cropRatioW: 1,  // 比例宽
        cropRatioH: 1,  // 比例高
        cropLockRatio: true,  // 是否锁定比例
        cropUseOriginalRatio: false,  // 是否使用原图比例
        cropOriginalMaxSize: 1024,  // 原图比例模式下的最长边
        cropFillBackground: false,  // 是否填充透明背景
        cropBackgroundColor: '#FFFFFF',  // 背景填充颜色
        isCropping: false,
        cropDragState: null,  // {index, startX, startY, startCropX, startCropY, type: 'move'|'resize', corner: 'nw'|'ne'|'sw'|'se'}

        showSaveCacheDialogVisible: false,
        showCacheManagerDialog: false,
        tempCacheList: [],
        cacheNameInput: '',
        cacheList: [],
        selectedCache: '',
        isCacheBusy: false,
        tempCacheSavedAt: '',
        
        // 批量文本操作
        batchTextAction: 'append',
        batchTextPosition: 'prefix',
        batchTextValue: '',
        pairResizeValue: 1536,  // 编辑模式图片裁切最长边
        
        // 训练分析器状态
        analyzerSubTab: 'pending',  // 'pending', 'curve', 'history'
        analyzerLogPath: '',
        analyzerResult: null,
        analyzerRecords: [],
        showMarkdownModal: false,
        markdownContent: '',
        pendingLogs: [],
        isDragOver: false,
        imagesDragOver: false,  // 文生图反推区域拖拽状态
        gridColumns: 4,  // 图片网格列数，默认4列
        pairGridColumns: 4,  // 编辑模式网格列数，默认4列
        aiAnalysisResult: '',
        analyzerSystemPrompt: '',  // 训练分析器系统提示词
        analyzerUserPrompt: '',    // 训练分析器用户提示词
        isAiAnalyzing: false,
        selectedRecordIds: [],
        selectedColors: {},
        compareMode: false,
        compareData: [],
        // 对比页右侧子标签（'curve' 或 'table'）
        compareRightTab: 'curve',
        
        // Chat 对话状态
        chatMessages: [],
        chatInput: '',
        isChatLoading: false,
        chatModel: 'Qwen/Qwen2.5-7B-Instruct',
        chatSessions: [],
        currentChatSessionId: null,
        currentSessionIndex: 0,
        currentStats: {},
        trainingCurveChart: null,
        top10Chart: null,
        showRecordDetail: false,
        recordDetail: null,

        // ==================== 辅助方法 ====================
        
        // 获取当前API Key（统一入口）
        get apiKey() {
            const provider = this.apikeyConfig.providers[this.apikeyConfig.current_provider];
            return provider ? provider.api_key : '';
        },
        
        // 获取当前Base URL（统一入口）
        get baseUrl() {
            const provider = this.apikeyConfig.providers[this.apikeyConfig.current_provider];
            return provider ? provider.base_url : '';
        },

        // 获取当前训练配置
        getCurrentConfig() {
            if (!this.analyzerResult) return null;

            if (this.analyzerResult.training_sessions && this.analyzerResult.training_sessions.length > 1) {
                // 多训练会话模式
                return this.analyzerResult.training_sessions[this.currentSessionIndex]?.config || null;
            } else {
                // 单训练模式
                return this.analyzerResult.config || null;
            }
        },

        // 检查是否有repeat数据（用于控制repeat列的显示/隐藏）
        hasRepeatData() {
            // 检查对比模式下的数据
            if (this.selectedRecordIds && this.selectedRecordIds.length > 0 && this.compareData && this.compareData.length > 0) {
                return this.compareData.some(rec => rec.repeats || rec.config?.repeats);
            }
            // 检查单条数据
            const config = this.getCurrentConfig();
            return config && config.repeats;
        },

        // 获取训练集数量
        getDatasetCount() {
            const config = this.getCurrentConfig();
            if (!config) return '-';
            // 优先显示已解析到的 dataset_count
            if (config.dataset_count != null) return config.dataset_count;
            // 回退显示目录名
            if (!config.train_data_dir) return '-';
            try {
                const pathParts = config.train_data_dir.split(/[/\\]/);
                const datasetName = pathParts[pathParts.length - 1];
                return datasetName || '-';
            } catch (e) {
                return '-';
            }
        },

        // 获取总步数
        getTotalSteps() {
            if (!this.analyzerResult) return '-';

            let valLosses = [];
            if (this.analyzerResult.training_sessions && this.analyzerResult.training_sessions.length > 1) {
                const session = this.analyzerResult.training_sessions[this.currentSessionIndex];
                valLosses = session ? session.val_losses : [];
            } else {
                valLosses = this.analyzerResult.val_losses || [];
            }

            if (valLosses.length === 0) return '-';

            const config = this.getCurrentConfig();

            // 如果解析器已经提取出 steps 字段（例如 2280），优先显示具体值
            if (config && config.steps) {
                return `${config.steps}`;
            }

            // 否则回退到估算：约X步/epoch × Ybatch
            const epochs = valLosses.length;
            const batchSize = config?.train_batch_size || 1;
            return `约${epochs}步/epoch × ${batchSize}batch`;
        },

        // 获取训练底模名称
        getBaseModelName() {
            const config = this.getCurrentConfig();
            if (!config) return '-';

            // 支持两种字段名：pretrained_model_name_or_path 或 pretrained_model（兼容旧日志解析）
            const modelPath = config.pretrained_model_name_or_path || config.pretrained_model;
            if (!modelPath) return '-';

            // 从路径中提取模型名称
            // 例如: /datasets/studio/huggingface/models/Qwen-Image-Edit-2509 -> Qwen-Image-Edit-2509
            try {
                const pathParts = modelPath.split(/[/\\]/);
                const modelName = pathParts[pathParts.length - 1];
                return modelName || '-';
            } catch (e) {
                return '-';
            }
        },

        // 获取训练时间
        getTrainingTime() {
            const config = this.getCurrentConfig();
            if (!config) return '-';
            // 如果解析器已经提取出 training_time 字段，直接返回（如 "4h"）
            if (config.training_time) return config.training_time;
            return '-';
        },

        // 通用文件选择
        async selectFileHelper(multiple = false) {
            try {
                if (window.pywebview && window.pywebview.api) {
                    // Desktop env: select_files method usually returns a list
                    // If the python API supports 'multiple' arg, we could use it, 
                    // but based on existing code it seems to take no args or we interpret the result.
                    // Let's assume it returns a list.
                    // If we want single, we just take the first one.
                    const paths = await window.pywebview.api.select_files();
                    if (paths && paths.length > 0) {
                        return multiple ? paths : paths[0];
                    }
                } else {
                    // Browser env
                    const result = await this.apiCall('system/select-files', 'POST', {
                        type: 'image',
                        multiple: multiple
                    });
                    if (result.success && result.paths && result.paths.length > 0) {
                        return multiple ? result.paths : result.paths[0];
                    }
                }
            } catch (error) {
                this.showNotification('文件选择失败: ' + error.message, 'error');
            }
            return multiple ? [] : null;
        },

        // ==================== 新增成对组 Modal 逻辑 ====================
        
        showAddPairModal: false,
        stagedPairs: [], // [{ id: number, left: string|null, right: string|null }]
        currentStagedIndex: 0,
        
        // 导入规则状态
        showImportRulesModal: false,
        importRules: {
            mode: 'default',  // 'default' | 'match' | 'manual'
            left_suffix: 'R',
            left2_suffix: 'G',
            right_suffix: 'T',
            txt_follows: 'right',  // txt跟随: 'left' 或 'right'
            manual_side: 'left' // 'left' | 'left2' | 'right' - where manual import places files
        },

        openAddPairModal() {
            this.stagedPairs = [];
            this.addStagedPair(); // 默认添加一个空组
            this.showAddPairModal = true;
        },

        closeAddPairModal() {
            this.showAddPairModal = false;
            this.stagedPairs = [];
            this.currentStagedIndex = 0;
        },

        addStagedPair() {
            this.stagedPairs.push({
                id: Date.now() + Math.random(),
                left: null,
                right: null
            });
            this.currentStagedIndex = this.stagedPairs.length - 1;
        },

        removeStagedPair(index, event) {
            if (event) event.stopPropagation();
            
            if (this.stagedPairs.length <= 1) {
                // 如果只剩一个，清空而不是删除
                this.stagedPairs[0].left = null;
                this.stagedPairs[0].right = null;
                this.currentStagedIndex = 0;
                return;
            }

            this.stagedPairs.splice(index, 1);
            
            // 如果删除的是当前前面的项，当前索引需要减1
            if (index < this.currentStagedIndex) {
                this.currentStagedIndex--;
            }
            
            // 确保索引不越界
            if (this.currentStagedIndex >= this.stagedPairs.length) {
                this.currentStagedIndex = Math.max(0, this.stagedPairs.length - 1);
            }
        },

        setCurrentStaged(index) {
            this.currentStagedIndex = index;
        },

        async selectStagedFile(side) {
            const path = await this.selectFileHelper(false);
            if (path) {
                // 使用后端API获取预览图
                try {
                    const result = await this.apiCall('preview', 'POST', { path });
                    if (result.success && result.thumbnail) {
                        this.stagedPairs[this.currentStagedIndex][side] = result.thumbnail;
                        // 保存原始路径用于提交
                        if (!this.stagedPairs[this.currentStagedIndex].raw) {
                            this.stagedPairs[this.currentStagedIndex].raw = {};
                        }
                        this.stagedPairs[this.currentStagedIndex].raw[side] = path;
                    } else {
                        // 降级：如果是Web环境可能直接用File对象，但这里我们只拿到了路径
                        // 对于本地文件路径，浏览器无法直接显示，必须通过后端转换
                        this.stagedPairs[this.currentStagedIndex][side] = null;
                        this.showNotification('无法预览图片', 'error');
                    }
                } catch (e) {
                    this.showNotification('预览失败: ' + e.message, 'error');
                }
            }
        },

        async confirmAddPairs() {
            const validPairs = this.stagedPairs.filter(p => (p.raw && p.raw.left) || (p.raw && p.raw.right)).map(p => ({
                left_path: p.raw ? p.raw.left : null,
                right_path: p.raw ? p.raw.right : null
            }));

            if (validPairs.length === 0) {
                this.closeAddPairModal();
                return;
            }

            this.showNotification('正在导入...', 'info');
            const result = await this.apiCall('pairs/add', 'POST', { pairs: validPairs });
            
            if (result.success) {
                this.pairs = result.pairs;
                this.showNotification(`成功添加 ${result.added} 组图片`, 'success');
                this.closeAddPairModal();
            }
        },

        // 初始化
        async init() {
            // 绑定全局事件处理函数（用于裁剪框拖动）
            this.handleGlobalCropDrag = this.handleGlobalCropDrag.bind(this);
            this.handleGlobalCropDragEnd = this.handleGlobalCropDragEnd.bind(this);
            
            // 先加载API Key配置（包含预存的激活码）
            await this.loadApikeyConfig();
            
            // 启动时优先校验授权文件，未授权则弹出设置并切换到激活页，阻止后续初始化
            try {
                const ok = await this.verifyLicenseOnStart();
                if (!ok) {
                    this.licenseStatus = '未检测到有效激活信息，请激活后重启程序或完成激活。';
                    this.showSettingsModal = true;
                    this.settingsTab = 'license';
                    // 不继续初始化（阻止程序运行）
                    return;
                }
            } catch (e) {
                console.debug('license verify error:', e && e.message);
                // 若校验异常，弹出设置页提示用户
                this.showSettingsModal = true;
                this.settingsTab = 'license';
                this.licenseStatus = '授权校验出错：' + (e && e.message);
                return;
            }

            this.loadTheme();  // 加载主题
            this.loadTranslateConfig();  // 加载翻译配置
            await this.loadConfig();
            await this.loadApikeyConfig();
            await this.loadAnalyzerSettings();  // 加载训练分析器设置
            await this.loadTemplateFiles();
            await this.loadImages();
            await this.loadPairs();
            await this.loadCacheList();
            await this.refreshCacheList();
            // 在初始化完成后尝试加载临时缓存（如果存在），以恢复上次临时保存的编辑状态
            try {
                await this.loadTempCacheOnStart();
            } catch (e) {
                // 静默失败，不打断初始化流程
                console.debug('load temp cache failed:', e && e.message);
            }
            this.initChat();
            this.loadSidebarTemplates();  // 加载侧边栏模板
        },
        
        // 加载API Key配置
        async loadApikeyConfig() {
            const result = await this.apiCall('apikey');
            if (result.success && result.config) {
                this.apikeyConfig = result.config;
                
                // 合并本地模型和后端默认模型（去重，排除隐藏的模型）
                const availableProviders = this.apikeyConfig.available_providers || {};
                for (const providerKey in this.apikeyConfig.providers) {
                    const provider = this.apikeyConfig.providers[providerKey];
                    const defaultProvider = availableProviders[providerKey];
                    
                    // 初始化隐藏模型列表
                    if (!provider.hiddenModels) {
                        provider.hiddenModels = [];
                    }
                    
                    // 获取后端默认模型
                    const defaultModels = (defaultProvider && defaultProvider.models) 
                        ? defaultProvider.models.map(m => ({ id: m, name: m })) 
                        : [];
                    
                    // 获取本地用户添加的模型
                    const userModels = provider.userModels || [];
                    
                    // 合并：用户添加的 + 兜底的，去重，排除隐藏的
                    const hiddenSet = new Set(provider.hiddenModels);
                    const mergedModels = [];
                    const existingIds = new Set();
                    
                    // 先添加用户模型
                    for (const model of userModels) {
                        if (!hiddenSet.has(model.id) && !existingIds.has(model.id)) {
                            mergedModels.push(model);
                            existingIds.add(model.id);
                        }
                    }
                    
                    // 再添加兜底模型
                    for (const model of defaultModels) {
                        if (!hiddenSet.has(model.id) && !existingIds.has(model.id)) {
                            mergedModels.push(model);
                            existingIds.add(model.id);
                        }
                    }
                    
                    provider.models = mergedModels;
                }
                
                // 获取当前渠道的模型列表
                const models = this.getCurrentProviderModels();
                
                // 同步到主界面配置
                this.config.current_provider = this.apikeyConfig.current_provider;
                this.config.model = this.apikeyConfig.model;
                this.chatModel = this.apikeyConfig.model;
                
                // 更新可用模型列表
                if (models.length > 0) {
                    this.availableModels = models.map(m => m.id || m.name);
                }
                
                // 从配置中读取预存的激活码
                if (this.apikeyConfig.license_code) {
                    this.licenseInput = this.apikeyConfig.license_code;
                }
            }
        },
        
        // 切换API渠道时的处理
        onProviderChange() {
            // 切换渠道后，自动选择该渠道的第一个模型
            const models = this.getCurrentProviderModels();
            if (models.length > 0) {
                this.apikeyConfig.model = models[0].id;
            } else {
                this.apikeyConfig.model = '';
            }
            this.saveApikeyConfig(true);
        },

        // 保存API Key配置
        async saveApikeyConfig(silent = false) {
            // 创建一个副本用于保存，避免修改原始数据
            const configToSave = JSON.parse(JSON.stringify(this.apikeyConfig));
            
            // 删除 available_providers，这是后端动态添加的
            delete configToSave.available_providers;
            
            // 保存激活码到配置
            configToSave.license_code = (this.licenseInput || '').trim();
            
            const result = await this.apiCall('apikey', 'POST', configToSave);
            if (result.success) {
                if (!silent) {
                    this.showNotification('配置已保存', 'success');
                }
            }
        },
        
        // ============== 授权 / 激活 相关 ==============
        // 获取本机机器码（直接显示原始 CPU UUID）
        async getLocalCpuHex() {
            try {
                const result = await this.apiCall('license/get_cpu_uuid');
                if (!(result && result.success && result.cpu_uuid)) {
                    this.showNotification(result && result.message ? result.message : '获取机器码失败', 'error');
                    this.licenseStatus = '获取机器码失败';
                    return;
                }

                // 直接显示原始 CPU UUID 作为机器码
                this.licenseCpuHex = result.cpu_uuid || '';
                this.licenseInput = '';
                
                // console.log('[DEBUG] 机器码:', result.cpu_uuid);
                // console.log('[DEBUG] 机器码长度:', result.cpu_uuid.length);
                // console.log('[DEBUG] 机器码HEX:', result.cpu_hex);
                
                this.licenseStatus = '已获取机器码，请将机器码发送给管理员获取激活码。';
            } catch (e) {
                this.showNotification('获取机器码出错: ' + (e && e.message), 'error');
                this.licenseStatus = '获取机器码出错';
            }
        },

        // 发起激活：将激活码写入后端本地文件
        async activateLicense() {
            try {
                const payload = {
                    license_code: (this.licenseInput || '').trim()
                };
                if (!payload.license_code) {
                    this.showNotification('请先填写激活码并点击激活', 'warning');
                    return;
                }
                const result = await this.apiCall('license/activate', 'POST', payload);
                if (result && result.success) {
                    this.licenseStatus = '激活成功，请重启应用以生效。';
                    this.showNotification('激活成功', 'success');
                    this.isLicensed = true;
                    // 激活成功后保存激活码到apikey.json，下次启动自动填充
                    await this.saveLicenseCode();
                } else {
                    this.licenseStatus = result.message || '激活失败';
                    this.showNotification(result.message || '激活失败', 'error');
                }
            } catch (e) {
                this.showNotification('激活出错: ' + (e && e.message), 'error');
                this.licenseStatus = '激活出错';
            }
        },

        // 启动时校验授权文件，返回 true/false
        async verifyLicenseOnStart() {
            try {
                const result = await this.apiCall('license/verify');
                if (result && result.success) {
                    this.isLicensed = true;
                    return true;
                } else {
                    this.isLicensed = false;
                    return false;
                }
            } catch (e) {
                console.debug('verifyLicenseOnStart error:', e && e.message);
                this.isLicensed = false;
                return false;
            }
        },

        // 从apikey.json加载预存的激活码
        async loadSavedLicenseCode() {
            try {
                // console.log('[DEBUG] Loading saved license code...');
                const result = await this.apiCall('license/get_saved_code');
                // console.log('[DEBUG] API result:', result);
                if (result && result.success && result.license_code) {
                    this.licenseInput = result.license_code;
                    // console.log('[DEBUG] Set licenseInput to:', this.licenseInput);
                }
            } catch (e) {
                console.debug('loadSavedLicenseCode error:', e && e.message);
            }
        },

        // 保存激活码到apikey.json
        async saveLicenseCode() {
            try {
                const code = (this.licenseInput || '').trim();
                await this.apiCall('license/save_code', 'POST', { license_code: code });
            } catch (e) {
                console.debug('saveLicenseCode error:', e && e.message);
            }
        },
        
        // 测试API连通性
        apiTestStatus: {},  // 存储每个渠道的测试状态
        async testApiConnection(providerKey) {
            const provider = this.apikeyConfig.providers[providerKey];
            if (!provider || !provider.api_key) {
                this.showNotification('请先填写API Key', 'warning');
                return;
            }
            
            // 设置测试中状态
            this.apiTestStatus[providerKey] = 'testing';
            
            try {
                const result = await this.apiCall('apikey/test', 'POST', {
                    api_key: provider.api_key,
                    base_url: provider.base_url,
                    model: this.apikeyConfig.model
                });
                
                if (result.success) {
                    this.apiTestStatus[providerKey] = 'success';
                    this.showNotification(result.message || '连接成功！', 'success');
                } else {
                    this.apiTestStatus[providerKey] = 'failed';
                    this.showNotification(result.message || '连接失败', 'error');
                }
            } catch (e) {
                this.apiTestStatus[providerKey] = 'failed';
                this.showNotification('测试失败: ' + e.message, 'error');
            }
            
            // 3秒后重置状态
            setTimeout(() => {
                this.apiTestStatus[providerKey] = '';
            }, 3000);
        },
        
        // 获取指定渠道的默认模型列表（优先使用后端下发的 available_providers）
        getDefaultProviderModels(providerKey) {
            const providers = this.apikeyConfig && this.apikeyConfig.available_providers;
            const info = providers && providers[providerKey];
            if (info && Array.isArray(info.models) && info.models.length > 0) {
                return info.models.map(m => ({ id: m, name: m }));
            }
            return this.availableModels.map(m => ({ id: m, name: m }));
        },

        // 获取当前渠道的模型列表
        getCurrentProviderModels() {
            const providerKey = this.apikeyConfig.current_provider;
            const provider = this.apikeyConfig.providers[providerKey];
            // 如果 models 数组存在且不为空，直接返回
            if (provider && Array.isArray(provider.models) && provider.models.length > 0) {
                return provider.models;
            }
            // 如果 models 不存在或为空数组，返回默认模型列表
            return this.getDefaultProviderModels(providerKey);
        },

        // 获取翻译厂商的模型列表（使用专用翻译模型）
        getTranslateProviderModels() {
            return this.translateModels[this.translateProvider] || [];
        },

        // 获取当前翻译模型的显示名称
        getTranslateModelDisplayName() {
            const models = this.translateModels[this.translateProvider] || [];
            const model = models.find(m => m.id === this.translateModelId);
            return model ? model.name : '选择模型';
        },

        // 选择翻译模型
        selectTranslateModel(provider, modelId) {
            this.translateProvider = provider;
            this.translateModelId = modelId;
            this.showTranslateModelDropdown = false;
            this.saveTranslateConfig();
        },

        // 获取厂商简称
        getProviderShortName(providerKey) {
            const names = {
                'modelscope': '魔搭',
                'siliconflow': '硅基',
                'tuzi': 'Tuzi'
            };
            return names[providerKey] || providerKey;
        },

        // 切换翻译厂商
        onTranslateProviderChange() {
            const models = this.getTranslateProviderModels();
            if (models.length > 0) {
                this.translateModelId = models[0].id;
            }
            // 保存翻译配置
            this.saveTranslateConfig();
        },
        
        // 保存翻译配置到本地存储
        saveTranslateConfig() {
            localStorage.setItem('translateProvider', this.translateProvider);
            localStorage.setItem('translateModelId', this.translateModelId);
        },
        
        // 加载翻译配置
        loadTranslateConfig() {
            const savedProvider = localStorage.getItem('translateProvider');
            const savedModelId = localStorage.getItem('translateModelId');
            if (savedProvider && this.translateModels[savedProvider]) {
                this.translateProvider = savedProvider;
            }
            if (savedModelId) {
                // 验证模型是否存在于当前厂商
                const models = this.getTranslateProviderModels();
                if (models.some(m => m.id === savedModelId)) {
                    this.translateModelId = savedModelId;
                } else if (models.length > 0) {
                    this.translateModelId = models[0].id;
                }
            }
        },
        
        // 打开模型管理弹窗
        openModelManageDialog() {
            this.showModelManageDialog = true;
        },

        // 恢复当前渠道默认（推荐）模型
        restoreDefaultModelsForCurrentProvider() {
            const providerKey = this.apikeyConfig.current_provider;
            const provider = this.apikeyConfig.providers[providerKey];
            if (!provider) return;

            // 清空隐藏列表和用户添加的模型
            provider.hiddenModels = [];
            provider.userModels = [];
            
            // 重新从后端获取默认模型
            const availableProviders = this.apikeyConfig.available_providers || {};
            const defaultProvider = availableProviders[providerKey];
            const defaultModels = (defaultProvider && defaultProvider.models) 
                ? defaultProvider.models.map(m => ({ id: m, name: m })) 
                : [];
            
            provider.models = defaultModels;

            if (provider.models.length > 0) {
                this.apikeyConfig.model = provider.models[0].id;
            }

            this.showNotification('已恢复默认模型', 'success');
            this.saveApikeyConfig(true);
        },
        
        // 打开添加模型弹窗
        openAddModelDialog() {
            this.editingModelIndex = -1;
            this.editingModel = { id: '', name: '' };
            this.showModelEditDialog = true;
        },
        
        // 打开编辑模型弹窗
        openEditModelDialog(index) {
            const provider = this.apikeyConfig.providers[this.apikeyConfig.current_provider];
            if (provider && provider.models && provider.models[index]) {
                this.editingModelIndex = index;
                this.editingModel = { ...provider.models[index] };
                this.showModelEditDialog = true;
            }
        },
        
        // 保存模型（添加或更新）
        saveModel() {
            if (!this.editingModel.id.trim()) {
                this.showNotification('模型ID不能为空', 'warning');
                return;
            }
            
            const providerKey = this.apikeyConfig.current_provider;
            const provider = this.apikeyConfig.providers[providerKey];
            
            // 初始化用户模型列表
            if (!Array.isArray(provider.userModels)) {
                provider.userModels = [];
            }
            if (!Array.isArray(provider.models)) {
                provider.models = [];
            }
            
            const modelData = {
                id: this.editingModel.id.trim(),
                name: this.editingModel.name.trim() || this.editingModel.id.trim()
            };
            
            if (this.editingModelIndex === -1) {
                // 添加新模型到用户模型列表
                provider.userModels.push(modelData);
                // 同时添加到显示列表
                provider.models.unshift(modelData);  // 添加到最前面
                this.showNotification('模型已添加', 'success');
            } else {
                // 更新现有模型
                provider.models[this.editingModelIndex] = modelData;
                // 同步更新用户模型列表
                const userIndex = provider.userModels.findIndex(m => m.id === this.editingModel.id);
                if (userIndex !== -1) {
                    provider.userModels[userIndex] = modelData;
                }
                this.showNotification('模型已更新', 'success');
            }
            
            this.showModelEditDialog = false;
            this.saveApikeyConfig();
        },
        
        // 删除模型（按索引）
        deleteModel(index) {
            const provider = this.apikeyConfig.providers[this.apikeyConfig.current_provider];
            if (provider && provider.models && provider.models[index]) {
                const modelName = provider.models[index].name || provider.models[index].id;
                provider.models.splice(index, 1);
                this.showNotification(`已删除模型: ${modelName}`, 'success');
                this.saveApikeyConfig();
            }
        },
        
        // 删除模型（按ID，用于下拉列表中的X按钮）
        deleteModelById(modelId) {
            const providerKey = this.apikeyConfig.current_provider;
            const provider = this.apikeyConfig.providers[providerKey];
            if (!provider) return;
            
            // 初始化隐藏模型列表
            if (!provider.hiddenModels) {
                provider.hiddenModels = [];
            }
            
            // 将模型加入隐藏列表
            if (!provider.hiddenModels.includes(modelId)) {
                provider.hiddenModels.push(modelId);
            }
            
            // 从显示列表中移除
            const index = provider.models.findIndex(m => m.id === modelId);
            if (index !== -1) {
                const modelName = provider.models[index].name || provider.models[index].id;
                provider.models.splice(index, 1);
                this.showNotification(`已隐藏: ${modelName}`, 'success');
                
                // 如果删除的是当前选中的模型，切换到第一个
                if (this.apikeyConfig.model === modelId) {
                    const models = this.getCurrentProviderModels();
                    this.apikeyConfig.model = models.length > 0 ? models[0].id : '';
                }
                this.saveApikeyConfig(true);
            }
        },
        
        // 加载模板文件列表
        async loadTemplateFiles() {
            const result = await this.apiCall('templates');
            if (result.success) {
                this.templateFiles = result.templates || [];
                
                // 将文件模板同步到 config.prompt_templates
                this.ensurePromptTemplates();
                
                // 处理 tagging 模式的模板
                const taggingFileTemplates = this.templateFiles.filter(t => t.mode === 'tagging');
                for (const tpl of taggingFileTemplates) {
                    const existingIdx = this.config.prompt_templates.tagging.templates.findIndex(
                        t => t.file_path === tpl.file_path || t.id === `file_${tpl.filename}`
                    );
                    const templateData = {
                        id: `file_${tpl.filename}`,
                        name: tpl.name,
                        system_prompt: tpl.system_prompt,
                        user_prompt: tpl.user_prompt,
                        file_path: tpl.file_path
                    };
                    if (existingIdx >= 0) {
                        this.config.prompt_templates.tagging.templates[existingIdx] = templateData;
                    } else {
                        this.config.prompt_templates.tagging.templates.push(templateData);
                    }
                }
                
                // 处理 editing 模式的模板
                const editingFileTemplates = this.templateFiles.filter(t => t.mode === 'editing');
                for (const tpl of editingFileTemplates) {
                    const existingIdx = this.config.prompt_templates.editing.templates.findIndex(
                        t => t.file_path === tpl.file_path || t.id === `file_${tpl.filename}`
                    );
                    const templateData = {
                        id: `file_${tpl.filename}`,
                        name: tpl.name,
                        system_prompt: tpl.system_prompt,
                        user_prompt: tpl.user_prompt,
                        file_path: tpl.file_path
                    };
                    if (existingIdx >= 0) {
                        this.config.prompt_templates.editing.templates[existingIdx] = templateData;
                    } else {
                        this.config.prompt_templates.editing.templates.push(templateData);
                    }
                }
                
                // 设置默认选中的模板
                if (taggingFileTemplates.length > 0 && !this.selectedTaggingTemplate) {
                    this.selectedTaggingTemplate = taggingFileTemplates[0].filename;
                }
                if (editingFileTemplates.length > 0 && !this.selectedEditingTemplate) {
                    this.selectedEditingTemplate = editingFileTemplates[0].filename;
                }
            }
        },
        
        // 选择模板时加载内容
        async onTemplateSelect(mode) {
            const filename = mode === 'tagging' ? this.selectedTaggingTemplate : this.selectedEditingTemplate;
            if (!filename) return;
            
            const result = await this.apiCall(`templates/${filename}`);
            if (result.success && result.template) {
                const tpl = result.template;
                // 更新当前模式的提示词
                this.ensurePromptTemplates();
                const pt = this.config.prompt_templates[mode];
                const current = pt.templates.find(t => String(t.id) === String(pt.selected));
                if (current) {
                    current.system_prompt = tpl.system_prompt || '';
                    current.user_prompt = tpl.user_prompt || '';
                    current.name = tpl.name || filename.replace('.json', '');
                }
                this.saveConfig();
            }
        },
        
        // 保存当前提示词为模板文件
        async saveAsTemplateFile() {
            const mode = this.settingsTab === 'tagging' ? 'tagging' : 'editing';
            const name = (this.newPromptTemplateName || '').trim();
            if (!name) {
                this.showNotification('请输入模板名称', 'warning');
                return;
            }
            
            const current = this.getCurrentPromptTemplate(mode);
            if (!current) return;
            
            const result = await this.apiCall('templates', 'POST', {
                name: name,
                mode: mode,
                system_prompt: current.system_prompt || '',
                user_prompt: current.user_prompt || ''
            });
            
            if (result.success) {
                this.showNotification('模板已保存', 'success');
                this.newPromptTemplateName = '';
                await this.loadTemplateFiles();
            }
        },
        
        // 更新模板文件
        async updateTemplateFile() {
            const mode = this.settingsTab === 'tagging' ? 'tagging' : 'editing';
            const filename = mode === 'tagging' ? this.selectedTaggingTemplate : this.selectedEditingTemplate;
            if (!filename) {
                this.showNotification('请先选择模板', 'warning');
                return;
            }
            
            const current = this.getCurrentPromptTemplate(mode);
            if (!current) return;
            
            const result = await this.apiCall(`templates/${filename}`, 'PUT', {
                name: current.name || filename.replace('.json', ''),
                mode: mode,
                system_prompt: current.system_prompt || '',
                user_prompt: current.user_prompt || ''
            });
            
            if (result.success) {
                this.showNotification('模板已更新', 'success');
                await this.loadTemplateFiles();
            }
        },
        
        // 删除模板文件
        async deleteTemplateFile() {
            const mode = this.settingsTab === 'tagging' ? 'tagging' : 'editing';
            const filename = mode === 'tagging' ? this.selectedTaggingTemplate : this.selectedEditingTemplate;
            if (!filename) {
                this.showNotification('请先选择模板', 'warning');
                return;
            }
            
            const result = await this.apiCall(`templates/${filename}`, 'DELETE');
            if (result.success) {
                this.showNotification('模板已删除', 'success');
                if (mode === 'tagging') {
                    this.selectedTaggingTemplate = '';
                } else {
                    this.selectedEditingTemplate = '';
                }
                await this.loadTemplateFiles();
            }
        },

        getCurrentPromptTemplate(mode) {
            const pt = this.config && this.config.prompt_templates ? this.config.prompt_templates[mode] : null;
            if (!pt || !Array.isArray(pt.templates)) return null;
            const selected = pt.selected;
            const found = pt.templates.find(t => t && String(t.id) === String(selected));
            return found || pt.templates.find(t => t) || null;
        },

        ensurePromptTemplates() {
            if (!this.config.prompt_templates) {
                this.config.prompt_templates = {
                    tagging: { selected: 'default', templates: [] },
                    editing: { selected: 'default', templates: [] }
                };
            }
            if (!this.config.prompt_templates.tagging) this.config.prompt_templates.tagging = { selected: 'default', templates: [] };
            if (!this.config.prompt_templates.editing) this.config.prompt_templates.editing = { selected: 'default', templates: [] };
            if (!Array.isArray(this.config.prompt_templates.tagging.templates)) this.config.prompt_templates.tagging.templates = [];
            if (!Array.isArray(this.config.prompt_templates.editing.templates)) this.config.prompt_templates.editing.templates = [];

            ['tagging', 'editing'].forEach(mode => {
                const pt = this.config.prompt_templates[mode];
                if (pt.selected !== undefined && pt.selected !== null) pt.selected = String(pt.selected);
                if (Array.isArray(pt.templates)) {
                    pt.templates.forEach(t => {
                        if (t && t.id !== undefined && t.id !== null) t.id = String(t.id);
                    });
                }
            });

            const ensureOne = (mode, defaultName) => {
                const pt = this.config.prompt_templates[mode];
                if (pt.templates.length === 0) {
                    pt.templates.push({
                        id: 'default',
                        name: defaultName,
                        system_prompt: this.config.system_prompt || '',
                        user_prompt: this.config.user_prompt || ''
                    });
                }
                if (!pt.selected || !pt.templates.some(t => t && String(t.id) === String(pt.selected))) {
                    pt.selected = pt.templates[0].id;
                }
            };

            ensureOne('tagging', '默认(单图反推)');
            ensureOne('editing', '默认(编辑模型)');
        },

        get selectedPromptTemplate() {
            this.ensurePromptTemplates();
            const mode = this.promptTemplateMode;
            const pt = this.config.prompt_templates[mode];
            const selected = pt.selected;
            return pt.templates.find(t => t && String(t.id) === String(selected)) || pt.templates.find(t => t) || null;
        },

        copyPromptTemplate() {
            this.ensurePromptTemplates();
            const mode = this.promptTemplateMode;
            const current = this.selectedPromptTemplate;
            if (!current) return;

            const id = String(Date.now());
            const tpl = {
                id,
                name: `${current.name || '模板'} (复制)`,
                system_prompt: current.system_prompt || '',
                user_prompt: current.user_prompt || ''
            };

            this.config.prompt_templates[mode].templates.push(tpl);
            this.config.prompt_templates[mode].selected = id;
            this.saveConfig();
        },

        saveAsPromptTemplate() {
            this.ensurePromptTemplates();
            const mode = this.promptTemplateMode;
            const name = (this.newPromptTemplateName || '').trim();
            if (!name) {
                this.showNotification('请输入模板名称', 'warning');
                return;
            }

            const current = this.getCurrentPromptTemplate(mode);
            const id = String(Date.now());
            const tpl = {
                id,
                name,
                system_prompt: current ? (current.system_prompt || '') : '',
                user_prompt: current ? (current.user_prompt || '') : ''
            };

            this.config.prompt_templates[mode].templates.push(tpl);
            this.config.prompt_templates[mode].selected = id;
            this.newPromptTemplateName = '';
            this.saveConfig();
        },

        deletePromptTemplate() {
            this.ensurePromptTemplates();
            const mode = this.promptTemplateMode;
            const pt = this.config.prompt_templates[mode];
            const selected = pt.selected;
            if (!Array.isArray(pt.templates) || pt.templates.length <= 1) {
                this.showNotification('至少保留一个模板', 'warning');
                return;
            }

            const idx = pt.templates.findIndex(t => t && t.id === selected);
            if (idx === -1) return;
            pt.templates.splice(idx, 1);
            pt.selected = pt.templates[0].id;
            this.saveConfig();
        },

        // 计算属性
        get selectedCount() {
            return this.images.filter(img => img.selected).length;
        },

        get selectedIds() {
            return this.images.filter(img => img.selected).map(img => img.id);
        },

        get selectedPairCount() {
            return this.pairs.filter(p => p.selected).length;
        },

        get selectedPairIds() {
            return this.pairs.filter(p => p.selected).map(p => p.id);
        },

        // API 调用
        async apiCall(endpoint, method = 'GET', data = null) {
            const options = {
                method,
                headers: {
                    'Content-Type': 'application/json'
                }
            };
            
            if (data) {
                options.body = JSON.stringify(data);
            }

            const response = await fetch(`/api/${endpoint}`, options);
            let result = null;
            try {
                const text = await response.text();
                result = text ? JSON.parse(text) : null;
            } catch (e) {
                result = null;
            }

            if (!result || typeof result !== 'object') {
                result = {
                    success: false,
                    message: `接口返回非JSON数据: /api/${endpoint} (HTTP ${response.status})`
                };
            }
            
            if (!result.success && result.message) {
                this.showNotification(result.message, 'error');
            }
            
            return result;
        },

        // 加载配置
        async loadConfig() {
            const result = await this.apiCall('config');
            if (result.success !== false) {
                this.config = result;
                this.ensurePromptTemplates();
            }
        },

        // ==================== 主题管理 ====================
        
        // 加载主题
        loadTheme() {
            const savedTheme = localStorage.getItem('app_theme');
            if (savedTheme && (savedTheme === 'light' || savedTheme === 'dark' || savedTheme === 'blue')) {
                this.theme = savedTheme;
            } else {
                this.theme = 'light';
            }
        },

        // 设置主题
        setTheme(newTheme) {
            this.theme = newTheme;
            localStorage.setItem('app_theme', newTheme);
            const themeNames = { light: '浅色', dark: '深色', blue: '深蓝' };
            this.showNotification(`已切换到${themeNames[newTheme]}模式`, 'success');
        },

        // ==================== 侧边栏模板管理 ====================
        
        // 加载侧边栏模板
        loadSidebarTemplates() {
            // 从config中加载当前选中的模板ID
            if (this.config.prompt_templates) {
                const taggingSelected = this.config.prompt_templates.tagging?.selected;
                const editingSelected = this.config.prompt_templates.editing?.selected;
                
                if (taggingSelected) {
                    this.selectedTaggingTemplateId = taggingSelected;
                }
                if (editingSelected) {
                    this.selectedEditingTemplateId = editingSelected;
                }
            }
        },

        // 获取当前模式的模板列表
        getCurrentModeTemplates() {
            const mode = this.modelMode === 'tagging' ? 'tagging' : 'editing';
            const templates = this.config.prompt_templates?.[mode]?.templates || [];
            return templates;
        },

        // 获取当前模板预览
        getCurrentTemplatePreview() {
            const mode = this.modelMode === 'tagging' ? 'tagging' : 'editing';
            const selectedId = mode === 'tagging' ? this.selectedTaggingTemplateId : this.selectedEditingTemplateId;
            const templates = this.getCurrentModeTemplates();
            const template = templates.find(t => t.id === selectedId);
            return template || { system_prompt: '', user_prompt: '' };
        },

        // 模板选择变更（修复x-model三元表达式问题）
        onTemplateSelectChange(newId) {
            const mode = this.modelMode === 'tagging' ? 'tagging' : 'editing';
            
            // 更新对应的模板ID
            if (mode === 'tagging') {
                this.selectedTaggingTemplateId = newId;
            } else {
                this.selectedEditingTemplateId = newId;
            }
            
            // 更新config中的selected
            if (!this.config.prompt_templates) {
                this.config.prompt_templates = {};
            }
            if (!this.config.prompt_templates[mode]) {
                this.config.prompt_templates[mode] = { templates: [], selected: 'default' };
            }
            this.config.prompt_templates[mode].selected = newId;
            
            // 保存配置
            this.saveConfig();
        },

        // 更新当前模板的字段
        updateCurrentTemplateField(field, value) {
            const mode = this.modelMode === 'tagging' ? 'tagging' : 'editing';
            const selectedId = mode === 'tagging' ? this.selectedTaggingTemplateId : this.selectedEditingTemplateId;
            
            this.ensurePromptTemplates();
            const templates = this.config.prompt_templates[mode]?.templates || [];
            const template = templates.find(t => t.id === selectedId);
            
            if (template) {
                template[field] = value;
            }
        },

        // 保存当前模板到文件
        async saveCurrentTemplateToFile() {
            const mode = this.modelMode === 'tagging' ? 'tagging' : 'editing';
            const selectedId = mode === 'tagging' ? this.selectedTaggingTemplateId : this.selectedEditingTemplateId;
            
            const templates = this.config.prompt_templates[mode]?.templates || [];
            const template = templates.find(t => t.id === selectedId);
            
            if (!template) return;
            
            // 如果是文件模板（有file_path），保存到文件
            if (template.file_path) {
                try {
                    const response = await fetch('/api/template-file/save', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            file_path: template.file_path,
                            system_prompt: template.system_prompt,
                            user_prompt: template.user_prompt
                        })
                    });
                    const result = await response.json();
                    if (!result.success) {
                        console.error('保存模板失败:', result.message);
                    }
                } catch (error) {
                    console.error('保存模板失败:', error);
                }
            } else {
                // 内置模板，保存到config
                this.saveConfig();
            }
        },

        // 侧边栏模板切换（保留兼容）
        onSidebarTemplateChange() {
            const mode = this.modelMode === 'tagging' ? 'tagging' : 'editing';
            const selectedId = mode === 'tagging' ? this.selectedTaggingTemplateId : this.selectedEditingTemplateId;
            
            // 更新config中的selected
            if (!this.config.prompt_templates) {
                this.config.prompt_templates = {};
            }
            if (!this.config.prompt_templates[mode]) {
                this.config.prompt_templates[mode] = { templates: [], selected: 'default' };
            }
            this.config.prompt_templates[mode].selected = selectedId;
            
            // 保存配置
            this.saveConfig();
            
            this.showNotification('模板已切换', 'success');
        },

        // 编辑当前模板
        async editCurrentTemplate() {
            // 重新加载配置和模板文件以确保显示最新数据
            console.log('[调试] 开始重新加载配置...');
            await this.loadConfig();
            console.log('[调试] 配置加载完成:', this.config.prompt_templates);
            await this.loadTemplateFiles();
            console.log('[调试] 模板文件加载完成:', this.config.prompt_templates);
            this.showPromptTemplateManager = true;
        },

        // 添加新模板
        async addNewTemplate() {
            // 重新加载配置和模板文件以确保显示最新数据
            await this.loadConfig();
            await this.loadTemplateFiles();
            this.showPromptTemplateManager = true;
        },

        // 创建新模板
        createNewTemplate() {
            const mode = this.modelMode === 'tagging' ? 'tagging' : 'editing';
            this.ensurePromptTemplates();
            
            const newId = 'template_' + Date.now();
            const newTemplate = {
                id: newId,
                name: '新模板',
                system_prompt: '',
                user_prompt: ''
            };
            
            this.config.prompt_templates[mode].templates.push(newTemplate);
            this.saveConfig();
            this.showNotification('新模板已创建', 'success');
        },

        // 删除模板
        deleteTemplate(templateId) {
            if (templateId === 'default') {
                this.showNotification('默认模板不能删除', 'warning');
                return;
            }
            
            const mode = this.modelMode === 'tagging' ? 'tagging' : 'editing';
            this.ensurePromptTemplates();
            
            const templates = this.config.prompt_templates[mode].templates;
            const index = templates.findIndex(t => t.id === templateId);
            
            if (index !== -1) {
                templates.splice(index, 1);
                
                // 如果删除的是当前选中的模板，切换到默认模板
                if (mode === 'tagging' && this.selectedTaggingTemplateId === templateId) {
                    this.selectedTaggingTemplateId = 'default';
                    this.config.prompt_templates[mode].selected = 'default';
                } else if (mode === 'editing' && this.selectedEditingTemplateId === templateId) {
                    this.selectedEditingTemplateId = 'default';
                    this.config.prompt_templates[mode].selected = 'default';
                }
                
                this.saveConfig();
                this.showNotification('模板已删除', 'success');
            }
        },

        // 确保 prompt_templates 结构存在
        ensurePromptTemplates() {
            if (!this.config.prompt_templates) {
                this.config.prompt_templates = {};
            }
            
            ['tagging', 'editing'].forEach(mode => {
                if (!this.config.prompt_templates[mode]) {
                    this.config.prompt_templates[mode] = {
                        selected: 'default',
                        templates: [
                            {
                                id: 'default',
                                name: '默认模板',
                                system_prompt: '',
                                user_prompt: ''
                            }
                        ]
                    };
                }
                
                // 确保至少有一个默认模板
                if (!this.config.prompt_templates[mode].templates || this.config.prompt_templates[mode].templates.length === 0) {
                    this.config.prompt_templates[mode].templates = [
                        {
                            id: 'default',
                            name: '默认模板',
                            system_prompt: '',
                            user_prompt: ''
                        }
                    ];
                }
            });
        },

        // 保存配置
        async saveConfig() {
            const result = await this.apiCall('config', 'POST', this.config);
            if (result.success) {
                this.showNotification('配置已保存', 'success');
            }
        },

        // 导出配置
        async exportConfig() {
            try {
                let path = null;
                if (window.pywebview && window.pywebview.api) {
                    path = await window.pywebview.api.save_file('config.json');
                } else {
                    const result = await this.apiCall('system/save-dialog', 'POST', { filename: 'config.json' });
                    if (result.success && result.path) {
                        path = result.path;
                    }
                }

                if (!path) return;

                // 获取当前完整配置
                const configResult = await this.apiCall('config');
                const configToSave = configResult.success !== false ? configResult : this.config;
                // 移除 backend 添加的临时字段 (如 available_providers)
                if (configToSave.available_providers) delete configToSave.available_providers;

                const writeResult = await this.apiCall('system/write-file', 'POST', {
                    path: path,
                    content: JSON.stringify(configToSave, null, 2)
                });

                if (writeResult.success) {
                    this.showNotification('配置导出成功', 'success');
                } else {
                    this.showNotification('导出失败: ' + writeResult.message, 'error');
                }
            } catch (error) {
                this.showNotification('导出出错: ' + error.message, 'error');
            }
        },

        // 导入配置
        async importConfig() {
            try {
                let path = null;
                if (window.pywebview && window.pywebview.api) {
                    // 使用 'log' 过滤器以支持 json 文件
                    const paths = await window.pywebview.api.select_files('log');
                    if (paths && paths.length > 0) path = paths[0];
                } else {
                    const result = await this.apiCall('system/select-files', 'POST', { type: 'log', multiple: false });
                    if (result.success && result.paths && result.paths.length > 0) {
                        path = result.paths[0];
                    }
                }

                if (!path) return;

                const readResult = await this.apiCall('system/read-file', 'POST', { path });
                if (readResult.success) {
                    try {
                        const newConfig = JSON.parse(readResult.content);
                        const saveResult = await this.apiCall('config', 'POST', newConfig);
                        if (saveResult.success) {
                            await this.loadConfig();
                            this.showNotification('配置导入成功', 'success');
                        }
                    } catch (e) {
                        this.showNotification('配置文件格式错误', 'error');
                    }
                } else {
                    this.showNotification('读取失败: ' + readResult.message, 'error');
                }
            } catch (error) {
                this.showNotification('导入出错: ' + error.message, 'error');
            }
        },

        // 加载图片列表
        async loadImages() {
            const result = await this.apiCall('images');
            if (result.success) {
                // 保留原有的 chineseText
                const oldChineseTexts = {};
                this.images.forEach(img => {
                    if (img.chineseText) {
                        oldChineseTexts[img.id] = img.chineseText;
                    }
                });
                
                // 更新图片列表
                this.images = result.images;
                
                // 恢复 chineseText
                this.images.forEach(img => {
                    if (oldChineseTexts[img.id]) {
                        img.chineseText = oldChineseTexts[img.id];
                    }
                });
            }
        },

        async loadPairs() {
            const result = await this.apiCall('pairs');
            if (result.success) {
                // 保留原有的 chineseText
                const oldChineseTexts = {};
                this.pairs.forEach(pair => {
                    if (pair.chineseText) {
                        oldChineseTexts[pair.id] = pair.chineseText;
                    }
                });
                
                // 更新图片对列表
                this.pairs = result.pairs;
                
                // 恢复 chineseText
                this.pairs.forEach(pair => {
                    if (oldChineseTexts[pair.id]) {
                        pair.chineseText = oldChineseTexts[pair.id];
                    }
                });
            }
        },

        async loadCacheList() {
            const result = await this.apiCall('cache/list');
            if (result.success) {
                this.cacheList = result.caches || [];
            }
        },

        showSaveCacheDialog() {
            const pad2 = (n) => String(n).padStart(2, '0');
            const d = new Date();
            const defaultName = `cache_${d.getFullYear()}${pad2(d.getMonth() + 1)}${pad2(d.getDate())}_${pad2(d.getHours())}${pad2(d.getMinutes())}${pad2(d.getSeconds())}`;
            this.cacheNameInput = defaultName;
            this.showSaveCacheDialogVisible = true;
        },

        async saveCache() {
            const name = (this.cacheNameInput || '').trim();
            if (!name) {
                this.showNotification('请输入缓存名称', 'warning');
                return;
            }
            if (this.isCacheBusy) return;
            this.isCacheBusy = true;
            try {
                const result = await this.apiCall('cache/save', 'POST', { name });
                if (result.success) {
                    this.showSaveCacheDialogVisible = false;
                    await this.loadCacheList();
                    this.selectedCache = name;
                    this.showNotification(result.message || '缓存已保存', 'success');
                }
            } finally {
                this.isCacheBusy = false;
            }
        },

        async saveTempCache() {
            if (this.isCacheBusy) return;
            this.isCacheBusy = true;
            try {
                // 生成唯一的缓存名称（时间戳）
                const d = new Date();
                const name = `cache_${d.getFullYear()}${String(d.getMonth()+1).padStart(2,'0')}${String(d.getDate()).padStart(2,'0')}_${String(d.getHours()).padStart(2,'0')}${String(d.getMinutes()).padStart(2,'0')}${String(d.getSeconds()).padStart(2,'0')}`;
                
                // 构建轻量化 pairs 列表，仅包含路径与必要字段，避免传输缩略图等大字段
                const lightweightPairs = (this.pairs || []).map(p => {
                    const left = p.left || null;
                    const right = p.right || null;
                    const left2 = p.left2 || null;
                    return {
                        id: p.id,
                        left: left ? { path: left.path } : null,
                        left2: left2 ? { path: left2.path } : null,
                        right: right ? { path: right.path } : null,
                        text: p.text || '',
                        status: p.status || 'idle',
                        selected: !!p.selected,
                        export_name: p.export_name || ''
                    };
                });

                const result = await this.apiCall('cache/save', 'POST', { name, pairs: lightweightPairs });
                if (result.success) {
                    this.showNotification(`缓存已保存: ${name}`, 'success');
                    // 刷新缓存列表
                    await this.refreshCacheList();
                } else {
                    this.showNotification(result.message || '保存失败', 'error');
                }
            } catch (e) {
                this.showNotification('保存失败: ' + e.message, 'error');
            } finally {
                this.isCacheBusy = false;
            }
        },

        async refreshCacheList() {
            try {
                const result = await this.apiCall('cache/list', 'GET');
                if (result.success) {
                    this.tempCacheList = result.caches || [];
                }
            } catch (e) {
                console.error('刷新缓存列表失败:', e);
            }
        },

        async loadCacheFromManager(cacheName) {
            if (this.isCacheBusy) return;
            
            if (!confirm(`确定要恢复缓存"${cacheName}"吗？当前未保存的编辑将丢失。`)) {
                return;
            }
            
            this.isCacheBusy = true;
            try {
                const result = await this.apiCall('cache/load', 'POST', { name: cacheName });
                if (result.success) {
                    // 确保pairs数据正确设置
                    this.pairs = result.pairs || [];
                    this.modelMode = 'editing';
                    this.showCacheManagerDialog = false;
                    this.showNotification(`已恢复缓存: ${cacheName}`, 'success');
                } else {
                    this.showNotification(result.message || '恢复失败', 'warning');
                }
            } catch (e) {
                this.showNotification('恢复失败: ' + e.message, 'error');
            } finally {
                this.isCacheBusy = false;
            }
        },

        // 删除单个缓存（缓存管理器中使用）
        async deleteSingleCache(cacheName) {
            if (!confirm(`确定要删除缓存"${cacheName}"吗？此操作不可恢复。`)) {
                return;
            }
            
            try {
                const result = await this.apiCall('cache/delete', 'POST', { name: cacheName });
                if (result.success) {
                    this.showNotification('缓存已删除', 'success');
                    await this.refreshCacheList();
                } else {
                    this.showNotification(result.message || '删除失败', 'error');
                }
            } catch (e) {
                this.showNotification('删除失败: ' + e.message, 'error');
            }
        },

        // 导出单个缓存
        async exportSingleCache(cacheName) {
            try {
                const result = await this.apiCall('cache/export', 'POST', { name: cacheName });
                if (result.success) {
                    this.showNotification(`缓存已导出: ${result.file}`, 'success');
                    // 可选：打开文件夹
                    if (confirm('是否打开导出文件夹？')) {
                        await this.apiCall('system/open-folder', 'POST', { path: result.file });
                    }
                } else {
                    this.showNotification(result.message || '导出失败', 'error');
                }
            } catch (e) {
                this.showNotification('导出失败: ' + e.message, 'error');
            }
        },

        // 一键清空所有缓存
        async clearAllCache() {
            // console.log('[DEBUG] clearAllCache called');
            // console.log('[DEBUG] tempCacheList.length:', this.tempCacheList.length);
            
            if (this.tempCacheList.length === 0) {
                this.showNotification('没有可清空的缓存', 'info');
                return;
            }
            
            if (!confirm(`确定要清空所有 ${this.tempCacheList.length} 个缓存吗？此操作不可恢复！`)) {
                // console.log('[DEBUG] user cancelled');
                return;
            }
            
            try {
                // console.log('[DEBUG] calling API cache/clear-all');
                const result = await this.apiCall('cache/clear-all', 'POST');
                // console.log('[DEBUG] API result:', result);
                if (result.success) {
                    this.showNotification(result.message || '已清空所有缓存', 'success');
                    await this.refreshCacheList();
                } else {
                    this.showNotification(result.message || '清空失败', 'error');
                }
            } catch (e) {
                // console.error('[DEBUG] clearAllCache error:', e);
                this.showNotification('清空失败: ' + e.message, 'error');
            }
        },

        // 一键导出所有缓存
        async exportAllCache() {
            // console.log('[DEBUG] exportAllCache called');
            // console.log('[DEBUG] tempCacheList.length:', this.tempCacheList.length);
            
            if (this.tempCacheList.length === 0) {
                this.showNotification('没有可导出的缓存', 'info');
                return;
            }
            
            try {
                // console.log('[DEBUG] calling API cache/export-all');
                this.showNotification('正在准备导出...', 'info');
                const result = await this.apiCall('cache/export-all', 'POST');
                // console.log('[DEBUG] API result:', result);
                if (result.success) {
                    this.showNotification(`已导出 ${result.count} 个缓存到: ${result.file}`, 'success');
                    // 可选：打开文件夹
                    if (confirm('是否打开导出文件夹？')) {
                        await this.apiCall('system/open-folder', 'POST', { path: result.file });
                    }
                } else {
                    this.showNotification(result.message || '导出失败', 'error');
                }
            } catch (e) {
                // console.error('[DEBUG] exportAllCache error:', e);
                this.showNotification('导出失败: ' + e.message, 'error');
            }
        },

        // 一键导入缓存
        async importAllCache() {
            try {
                const result = await this.apiCall('cache/import-all', 'POST');
                if (result.success) {
                    this.showNotification(result.message || '缓存已导入', 'success');
                    await this.refreshCacheList();
                } else {
                    this.showNotification(result.message || '导入失败', 'error');
                }
            } catch (e) {
                this.showNotification('导入失败: ' + e.message, 'error');
            }
        },

        // 恢复上一次临时保存（不弹确认，直接覆盖当前未保存状态）
        async restoreTempCache() {
            if (this.isCacheBusy) return;
            this.isCacheBusy = true;
            try {
                const name = '__temp_cache__';
                const result = await this.apiCall('cache/load', 'POST', { name });
                if (result.success && result.pairs) {
                    this.pairs = result.pairs;
                    this.modelMode = 'editing';
                    this.showNotification(result.message || '已恢复上次临时保存的内容', 'success');
                } else {
                    this.showNotification(result.message || '恢复失败，未找到临时保存内容', 'warning');
                }
            } catch (e) {
                this.showNotification('恢复失败: ' + e.message, 'error');
            } finally {
                this.isCacheBusy = false;
            }
        },

        // 启动时静默加载临时缓存（如果存在则恢复，不弹确认）
        async loadTempCacheOnStart() {
            if (this.isCacheBusy) return;
            this.isCacheBusy = true;
            try {
                const name = '__temp_cache__';
                const result = await this.apiCall('cache/load', 'POST', { name });
                if (result && result.success && result.pairs) {
                    this.pairs = result.pairs;
                    this.modelMode = 'editing';
                    // 更新已保存时间戳（如果后端没有返回具体时间，使用当前时间）
                    const d = new Date();
                    const stamp = `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}:${String(d.getSeconds()).padStart(2,'0')}`;
                    this.tempCacheSavedAt = stamp;
                }
            } catch (e) {
                // 忽略错误
            } finally {
                this.isCacheBusy = false;
            }
        },

        async loadCache() {
            const name = (this.selectedCache || '').trim();
            if (!name) return;
            if (this.isCacheBusy) return;
            this.isCacheBusy = true;
            try {
                const ok = await this.confirmAction('加载缓存', `确定加载缓存 “${name}” 吗？当前未保存的修改会丢失。`);
                if (!ok) return;
                const result = await this.apiCall('cache/load', 'POST', { name });
                if (result.success && result.pairs) {
                    this.pairs = result.pairs;
                    this.modelMode = 'editing';
                    this.showNotification(result.message || '缓存已加载', 'success');
                }
            } finally {
                this.isCacheBusy = false;
            }
        },

        async deleteCache() {
            const name = (this.selectedCache || '').trim();
            if (!name) return;
            if (this.isCacheBusy) return;
            const ok = await this.confirmAction('删除缓存', `确定删除缓存 “${name}” 吗？此操作不可恢复。`);
            if (!ok) return;
            this.isCacheBusy = true;
            try {
                const result = await this.apiCall('cache/delete', 'POST', { name });
                if (result.success) {
                    this.showNotification(result.message || '缓存已删除', 'success');
                    this.selectedCache = '';
                    await this.loadCacheList();
                }
            } finally {
                this.isCacheBusy = false;
            }
        },

        // 处理文生图反推区域的拖拽导入
        async handleImagesDrop(event) {
            this.imagesDragOver = false;
            
            const files = event.dataTransfer.files;
            if (!files || files.length === 0) return;
            
            // 收集图片文件和文本文件
            const imageFiles = [];
            const textFiles = {};
            const imageExtensions = ['.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif'];
            
            for (const file of files) {
                const fileName = file.name.toLowerCase();
                const ext = fileName.substring(fileName.lastIndexOf('.'));
                
                if (imageExtensions.includes(ext)) {
                    imageFiles.push(file);
                } else if (ext === '.txt') {
                    // 记录文本文件，用文件名（不含扩展名）作为 key
                    const baseName = file.name.substring(0, file.name.lastIndexOf('.'));
                    textFiles[baseName.toLowerCase()] = file;
                }
            }
            
            if (imageFiles.length === 0) {
                alert('未找到支持的图片文件');
                return;
            }
            
            // 上传图片和匹配的文本
            const formData = new FormData();
            
            for (const imgFile of imageFiles) {
                formData.append('images', imgFile);
                
                // 查找匹配的文本文件
                const baseName = imgFile.name.substring(0, imgFile.name.lastIndexOf('.')).toLowerCase();
                if (textFiles[baseName]) {
                    formData.append('texts', textFiles[baseName]);
                    formData.append('text_matches', baseName);  // 记录匹配关系
                }
            }
            
            try {
                const response = await fetch('/api/images/upload-drop', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                if (result.success) {
                    this.images = result.images;
                    // 直接加载，无需二次确认
                } else {
                    alert('导入失败: ' + (result.message || '未知错误'));
                }
            } catch (error) {
                alert('导入失败: ' + error.message);
            }
        },

        // 选择图片（通过文件选择器）
        async selectImages() {
            try {
                // 检查是否在 pywebview 桌面环境
                if (window.pywebview && window.pywebview.api) {
                    // 使用原生文件选择对话框
                    const paths = await window.pywebview.api.select_files();
                    if (paths && paths.length > 0) {
                        await this.addImages(paths);
                    }
                } else {
                    // 浏览器模式：使用后端 API 调用系统对话框
                    const result = await this.apiCall('system/select-files', 'POST', {
                        type: 'image',
                        multiple: true
                    });
                    
                    if (result.success && result.paths && result.paths.length > 0) {
                        await this.addImages(result.paths);
                    }
                }
            } catch (error) {
                this.showNotification('文件选择失败: ' + error.message, 'error');
            }
        },

        // 选择文件夹
        async selectFolder() {
            try {
                // 检查是否在 pywebview 桌面环境
                if (window.pywebview && window.pywebview.api) {
                    // 使用原生文件夹选择对话框
                    const path = await window.pywebview.api.select_folder();
                    if (path) {
                        const result = await this.apiCall('select-folder', 'POST', { path });
                        if (result.success) {
                            this.images = result.images;
                            this.showNotification(`已添加 ${result.added} 张图片`, 'success');
                        }
                    }
                } else {
                    // 浏览器模式：使用后端 API 调用系统对话框
                    const result = await this.apiCall('system/select-folder', 'POST');
                    
                    if (result.success && result.path) {
                        const folderResult = await this.apiCall('select-folder', 'POST', { path: result.path });
                        if (folderResult.success) {
                            this.images = folderResult.images;
                            this.showNotification(`已添加 ${folderResult.added} 张图片`, 'success');
                        }
                    }
                }
            } catch (error) {
                this.showNotification('文件夹选择失败: ' + error.message, 'error');
            }
        },

        // 添加图片
        async addImages(paths) {
            const result = await this.apiCall('images/add', 'POST', { paths });
            if (result.success) {
                this.images = result.images;
                this.showNotification(`已添加 ${result.added} 张图片`, 'success');
            }
        },

        async addEmptyPair() {
            const result = await this.apiCall('pairs/add', 'POST', {
                pairs: [{ create_empty: true }]
            });
            if (result.success) {
                this.pairs = result.pairs;
            }
        },

        async selectPairImages() {
            try {
                let paths = [];
                if (window.pywebview && window.pywebview.api) {
                    paths = await window.pywebview.api.select_files();
                } else {
                    const result = await this.apiCall('system/select-files', 'POST', {
                        type: 'image',
                        multiple: true
                    });
                    if (result.success && result.paths) {
                        paths = result.paths;
                    }
                }

                if (!paths || paths.length === 0) return;

                const pairs = [];
                for (let i = 0; i < paths.length; i += 2) {
                    pairs.push({
                        left_path: paths[i],
                        right_path: (i + 1 < paths.length) ? paths[i + 1] : null
                    });
                }

                const addResult = await this.apiCall('pairs/add', 'POST', { pairs });
                if (addResult.success) {
                    this.pairs = addResult.pairs;
                    this.showNotification(`已添加 ${addResult.added} 组图片`, 'success');
                }
            } catch (error) {
                this.showNotification('文件选择失败: ' + error.message, 'error');
            }
        },

        async selectPairFolder() {
            this.showImportRulesModal = true;
        },

        async confirmImportFolder() {
            try {
                let folderPath = null;
                if (window.pywebview && window.pywebview.api) {
                    folderPath = await window.pywebview.api.select_folder();
                } else {
                    const result = await this.apiCall('system/select-folder', 'POST');
                    if (result.success && result.path) {
                        folderPath = result.path;
                    }
                }

                if (!folderPath) return;

                // 立即关闭规则弹窗，显示加载状态
                this.showImportRulesModal = false;
                this.isImporting = true;
                this.importProgress = 0;
                this.importProgressText = '正在扫描文件夹...';
                
                // 如果是手动导入模式，我们也把 manual_side 发给后端
                const payload = { 
                    path: folderPath,
                    mode: this.importRules.mode || 'default',
                    left_suffix: this.importRules.left_suffix || 'R',
                    left2_suffix: this.importRules.left2_suffix || 'G',
                    right_suffix: this.importRules.right_suffix || 'T',
                    txt_follows: this.importRules.txt_follows || 'right'
                };
                if (this.importRules.mode === 'manual') {
                    payload.manual_side = this.importRules.manual_side || 'left';
                }

                const importResult = await this.apiCall('pairs/import-folder', 'POST', payload);
                
                this.isImporting = false;
                
                if (importResult.success) {
                    this.pairs = importResult.pairs;
                    this.showNotification(`已导入 ${importResult.added} 组匹配图片`, 'success');
                } else {
                    this.showNotification(importResult.message, 'warning');
                }
            } catch (error) {
                this.isImporting = false;
                this.showNotification('文件夹选择失败: ' + error.message, 'error');
            }
        },

        async selectPairSide(pairId, side) {
            try {
                let path = null;
                if (window.pywebview && window.pywebview.api) {
                    const paths = await window.pywebview.api.select_files();
                    path = (paths && paths.length > 0) ? paths[0] : null;
                } else {
                    const result = await this.apiCall('system/select-files', 'POST', {
                        type: 'image',
                        multiple: false
                    });
                    path = (result.success && result.paths && result.paths.length > 0) ? result.paths[0] : null;
                }

                if (!path) return;

                let payload = {};
                if (side === 'left') {
                    payload = { left_path: path };
                } else if (side === 'left2') {
                    payload = { left2_path: path };
                } else {
                    payload = { right_path: path };
                }
                const updateResult = await this.apiCall(`pairs/${pairId}`, 'PUT', payload);
                if (updateResult.success) {
                    const index = this.pairs.findIndex(p => p.id === pairId);
                    if (index !== -1) {
                        this.pairs[index] = updateResult.pair;
                    }
                    if (this.detailPair && this.detailPair.id === pairId) {
                        this.detailPair = { ...updateResult.pair };
                    }
                }
            } catch (error) {
                this.showNotification('文件选择失败: ' + error.message, 'error');
            }
        },

        async handlePairImageDrop(event, side) {
            if (!this.detailPair) return;
            
            const files = event.dataTransfer.files;
            if (!files || files.length === 0) return;
            
            const file = files[0];
            // 检查是否为图片文件
            if (!file.type.startsWith('image/')) {
                this.showNotification('请拖拽图片文件', 'warning');
                return;
            }
            
            // 使用FormData上传文件
            const formData = new FormData();
            formData.append('file', file);
            formData.append('side', side);
            
            try {
                this.showNotification('正在上传图片...', 'info');
                const response = await fetch(`/api/pairs/${this.detailPair.id}/upload-image`, {
                    method: 'POST',
                    body: formData
                });
                const result = await response.json();
                
                if (result.success) {
                    // 更新pairs列表
                    const index = this.pairs.findIndex(p => p.id === this.detailPair.id);
                    if (index !== -1) {
                        this.pairs[index] = result.pair;
                    }
                    // 更新详情弹窗
                    this.detailPair = { ...result.pair };
                    this.showNotification('图片上传成功', 'success');
                } else {
                    this.showNotification(result.message || '上传失败', 'error');
                }
            } catch (error) {
                this.showNotification('上传失败: ' + error.message, 'error');
            }
        },

        // 切换选中状态
        toggleSelect(imageId) {
            const image = this.images.find(img => img.id === imageId);
            if (image) {
                image.selected = !image.selected;
            }
        },

        // 全选
        selectAll() {
            const allSelected = this.images.every(img => img.selected);
            this.images.forEach(img => img.selected = !allSelected);
        },

        // 打开详情
        openDetail(imageId) {
            this.detailImage = { ...this.images.find(img => img.id === imageId) };
            this.originalDetailImageText = this.detailImage?.text || '';
            this.showTranslateLangDropdown = false;
            this.showTranslateModelDropdown = false;
            // 如果已有翻译文本，初始化并渲染句子标记
            if (this.detailImage?.translatedText) {
                this.updateSentenceMapping();
                this.initSentenceDataStore();
                this.$nextTick(() => {
                    this.renderMarkedTranslatedHtml();
                });
            } else {
                // 清空句子数据存储
                this.sentenceDataStore = [];
            }
        },

        openPairDetail(pairId) {
            this.detailPair = { ...this.pairs.find(p => p.id === pairId) };
            this.originalDetailPairText = this.detailPair?.text || '';
            this.showTranslateLangDropdown = false;
            this.showTranslateModelDropdown = false;
            // 如果已有翻译文本，初始化并渲染句子标记
            if (this.detailPair?.translatedText) {
                this.updateSentenceMapping();
                this.initSentenceDataStore();
                this.$nextTick(() => {
                    this.renderMarkedOriginalHtmlForPair();
                    this.renderMarkedTranslatedHtmlForPair();
                });
            } else {
                // 清空句子数据存储
                this.sentenceDataStore = [];
            }
        },

        // 获取当前详情图片的索引
        get detailImageIndex() {
            if (!this.detailImage) return -1;
            return this.images.findIndex(img => img.id === this.detailImage.id);
        },

        // 导航到前一张/后一张图片
        navigateDetailImage(direction) {
            if (!this.detailImage) return;
            
            // 检查是否有修改
            const hasChanges = this.detailImage.text !== this.originalDetailImageText;
            
            if (hasChanges) {
                const action = confirm('当前图片有未保存的修改，是否保存？\n\n点击"确定"保存并跳转，点击"取消"放弃修改并跳转。');
                if (action) {
                    // 保存当前修改
                    this.saveDetail().then(() => {
                        this.doNavigateDetailImage(direction);
                    });
                    return;
                }
            }
            
            this.doNavigateDetailImage(direction);
        },

        // 实际执行图片导航
        doNavigateDetailImage(direction) {
            const currentIndex = this.detailImageIndex;
            const newIndex = currentIndex + direction;
            
            if (newIndex >= 0 && newIndex < this.images.length) {
                this.detailImage = { ...this.images[newIndex] };
                this.originalDetailImageText = this.detailImage?.text || '';
                this.showTranslateLangDropdown = false;
                this.showTranslateModelDropdown = false;
            }
        },

        get detailPairIndex() {
            if (!this.detailPair) return -1;
            return this.pairs.findIndex(p => p.id === this.detailPair.id);
        },

        navigatePair(direction) {
            if (!this.detailPair) return;
            
            // 检查是否有修改
            const hasChanges = this.detailPair.text !== this.originalDetailPairText;
            
            if (hasChanges) {
                const action = confirm('当前图片组有未保存的修改，是否保存？\n\n点击"确定"保存并跳转，点击"取消"放弃修改并跳转。');
                if (action) {
                    // 保存当前修改
                    this.savePairDetail().then(() => {
                        this.doNavigatePair(direction);
                    });
                    return;
                }
            }
            
            this.doNavigatePair(direction);
        },

        // 实际执行成对导航
        doNavigatePair(direction) {
            const currentIndex = this.detailPairIndex;
            const newIndex = currentIndex + direction;
            if (newIndex >= 0 && newIndex < this.pairs.length) {
                this.detailPair = { ...this.pairs[newIndex] };
                this.originalDetailPairText = this.detailPair?.text || '';
                this.showTranslateLangDropdown = false;
                this.showTranslateModelDropdown = false;
            }
        },

        navigatePairWrap(direction) {
            if (!this.detailPair) return;
            if (!Array.isArray(this.pairs) || this.pairs.length === 0) return;

            // 检查是否有修改
            const hasChanges = this.detailPair.text !== this.originalDetailPairText;
            
            if (hasChanges) {
                const action = confirm('当前图片组有未保存的修改，是否保存？\n\n点击"确定"保存并跳转，点击"取消"放弃修改并跳转。');
                if (action) {
                    this.savePairDetail().then(() => {
                        this.doNavigatePairWrap(direction);
                    });
                    return;
                }
            }
            
            this.doNavigatePairWrap(direction);
        },

        // 实际执行循环导航
        doNavigatePairWrap(direction) {
            const currentIndex = this.detailPairIndex;
            if (currentIndex < 0) return;

            let newIndex = (currentIndex + direction) % this.pairs.length;
            if (newIndex < 0) newIndex += this.pairs.length;
            this.detailPair = { ...this.pairs[newIndex] };
            this.originalDetailPairText = this.detailPair?.text || '';
            this.showTranslateLangDropdown = false;
            this.showTranslateModelDropdown = false;
        },

        handlePairDetailArrow(direction, currentSide) {
            if (!this.detailPair) return currentSide;
            const side = currentSide === 'right' ? 'right' : 'left';
            const dir = direction >= 0 ? 1 : -1;

            if (dir === 1) {
                if (side === 'left') {
                    return 'right';
                }
                this.navigatePairWrap(1);
                return 'left';
            }

            if (side === 'right') {
                return 'left';
            }
            this.navigatePairWrap(-1);
            return 'right';
        },

        // 保存详情
        async saveDetail() {
            if (!this.detailImage) return;
            
            const result = await this.apiCall(`images/${this.detailImage.id}`, 'PUT', {
                text: this.detailImage.text
            });
            
            if (result.success) {
                const index = this.images.findIndex(img => img.id === this.detailImage.id);
                if (index !== -1) {
                    this.images[index] = result.image;
                }
                this.detailImage = null;
                this.originalDetailImageText = '';
                this.showNotification('保存成功', 'success');
            }
        },

        // 取消详情编辑（带确认）
        cancelDetailEdit() {
            if (!this.detailImage) return;
            
            // 检查是否有修改
            const hasChanges = this.detailImage.text !== this.originalDetailImageText;
            
            if (hasChanges) {
                if (confirm('是否放弃当前修改？')) {
                    this.detailImage = null;
                    this.originalDetailImageText = '';
                }
            } else {
                this.detailImage = null;
                this.originalDetailImageText = '';
            }
        },

        // 关闭详情弹窗（带确认）
        closeDetailWithConfirm() {
            this.cancelDetailEdit();
        },

        async savePairDetail() {
            if (!this.detailPair) return;

            const result = await this.apiCall(`pairs/${this.detailPair.id}`, 'PUT', {
                text: this.detailPair.text
            });

            if (result.success) {
                const index = this.pairs.findIndex(p => p.id === this.detailPair.id);
                if (index !== -1) {
                    this.pairs[index] = result.pair;
                }
                this.detailPair = null;
                this.originalDetailPairText = '';
                this.showNotification('保存成功', 'success');
            }
        },

        // 取消成对详情编辑（带确认）
        cancelPairDetailEdit() {
            if (!this.detailPair) return;
            
            // 检查是否有修改
            const hasChanges = this.detailPair.text !== this.originalDetailPairText;
            
            if (hasChanges) {
                if (confirm('是否放弃当前修改？')) {
                    this.detailPair = null;
                    this.originalDetailPairText = '';
                }
            } else {
                this.detailPair = null;
                this.originalDetailPairText = '';
            }
        },

        // 关闭成对详情弹窗（带确认）
        closePairDetailWithConfirm() {
            this.cancelPairDetailEdit();
        },

        // 删除当前详情组
        async deletePairDetail() {
            if (!this.detailPair) return;
            const confirmed = confirm('确认要删除此图片组吗？此操作不可恢复。');
            if (!confirmed) return;

            const pairId = this.detailPair.id;
            const result = await this.apiCall(`pairs/${pairId}`, 'DELETE');
            if (result && result.success) {
                // 从本地列表中移除
                const index = this.pairs.findIndex(p => p.id === pairId);
                if (index !== -1) {
                    this.pairs.splice(index, 1);
                }
                this.detailPair = null;
                this.showNotification('已删除该组', 'success');
            } else {
                this.showNotification(result && result.message ? result.message : '删除失败', 'error');
            }
        },

        async applyBatchText() {
            if (this.selectedPairCount === 0) {
                this.showNotification('请先选择要操作的组', 'warning');
                return;
            }
            
            if (this.batchTextAction === 'append' && !this.batchTextValue.trim()) {
                this.showNotification('请输入文本内容', 'warning');
                return;
            }
            
            // 图片裁切操作
            if (this.batchTextAction === 'resize') {
                const maxSize = parseInt(this.pairResizeValue) || 1536;
                this.showNotification('正在裁切图片...', 'info');
                const result = await this.apiCall('pairs/resize', 'POST', {
                    ids: this.selectedPairIds,
                    max_size: maxSize
                });
                if (result.success) {
                    this.showNotification(result.message, 'success');
                    await this.loadPairs();
                }
                return;
            }
            
            const selectedIds = this.selectedPairIds;
            let successCount = 0;
            
            for (const pairId of selectedIds) {
                const pair = this.pairs.find(p => p.id === pairId);
                if (!pair) continue;
                
                let newText = '';
                if (this.batchTextAction === 'clear') {
                    newText = '';
                } else if (this.batchTextAction === 'append') {
                    const currentText = pair.text || '';
                    if (this.batchTextPosition === 'prefix') {
                        newText = currentText ? `${this.batchTextValue.trim()}, ${currentText}` : this.batchTextValue.trim();
                    } else {
                        newText = currentText ? `${currentText}, ${this.batchTextValue.trim()}` : this.batchTextValue.trim();
                    }
                }
                
                const result = await this.apiCall(`pairs/${pairId}`, 'PUT', { text: newText });
                if (result.success) {
                    pair.text = newText;
                    successCount++;
                }
            }
            
            const actionText = this.batchTextAction === 'clear' ? '清空' : '添加';
            this.showNotification(`已${actionText} ${successCount} 组文本`, 'success');
        },

        togglePairSelect(pairId) {
            const pair = this.pairs.find(p => p.id === pairId);
            if (pair) {
                pair.selected = !pair.selected;
            }
        },

        // 清除pair的某一侧图片
        async clearPairSide(side) {
            if (!this.detailPair) return;
            
            try {
                const result = await this.apiCall(`pairs/${this.detailPair.id}`, 'PUT', {
                    [side]: null
                });
                
                if (result.success) {
                    this.detailPair[side] = null;
                    const index = this.pairs.findIndex(p => p.id === this.detailPair.id);
                    if (index !== -1) {
                        this.pairs[index][side] = null;
                    }
                    this.showNotification('已删除图片', 'success');
                }
            } catch (error) {
                this.showNotification('删除失败: ' + error.message, 'error');
            }
        },

        selectAllPairs() {
            const allSelected = this.pairs.length > 0 && this.pairs.every(p => p.selected);
            this.pairs.forEach(p => p.selected = !allSelected);
        },

        async deleteSelectedPairs() {
            if (this.selectedPairCount === 0) {
                this.showNotification('请先选择要删除的组', 'warning');
                return;
            }

            if (!await this.confirmAction('确认删除', `确定要删除所选的 ${this.selectedPairCount} 组图片吗？\n此操作仅从列表中移除，不会删除源文件。`)) return;

            try {
                const idsToDelete = [...this.selectedPairIds];
                let successCount = 0;
                let failedCount = 0;

                // 开始进度显示
                this.isProcessing = true;
                this.taskStatus = {
                    total: idsToDelete.length,
                    completed: 0,
                    failed: 0,
                    current_index: 0,
                    current_name: ''
                };

                for (let i = 0; i < idsToDelete.length; i++) {
                    const id = idsToDelete[i];
                    this.taskStatus.current_index = i + 1;
                    this.taskStatus.current_name = `删除组 ${id}`;

                    try {
                        const result = await this.apiCall(`pairs/${id}`, 'DELETE');
                        if (result.success) {
                            successCount++;
                        } else {
                            failedCount++;
                        }
                    } catch (error) {
                        console.error(`删除组 ${id} 失败:`, error);
                        failedCount++;
                    }

                    // 更新进度
                    this.taskStatus.completed = successCount + failedCount;
                    this.taskStatus.failed = failedCount;

                    // 更新进度百分比
                    this.progress = (this.taskStatus.completed / this.taskStatus.total) * 100;
                }

                await this.loadPairs();

                // 隐藏进度条
                this.isProcessing = false;
                this.progress = 0;

                if (failedCount === 0) {
                    this.showNotification(`已成功删除 ${successCount} 组图片`, 'success');
                } else {
                    this.showNotification(`删除完成: ${successCount} 成功, ${failedCount} 失败`, failedCount === 0 ? 'success' : 'warning');
                }
            } catch (error) {
                // 隐藏进度条
                this.isProcessing = false;
                this.progress = 0;
                this.showNotification('删除失败: ' + error.message, 'error');
            }
        },

        // 单个删除（无确认）
        async deleteSinglePair(pairId) {
            try {
                const result = await this.apiCall(`pairs/${pairId}`, 'DELETE');
                if (result.success) {
                    // 从本地数组移除
                    const index = this.pairs.findIndex(p => p.id === pairId);
                    if (index !== -1) {
                        this.pairs.splice(index, 1);
                    }
                    this.showNotification('已删除', 'success');
                }
            } catch (error) {
                this.showNotification('删除失败: ' + error.message, 'error');
            }
        },

        openExportDialog() {
            if (this.selectedPairCount === 0) {
                this.showNotification('请先选择要导出的组', 'warning');
                return;
            }
            this.showExportDialog = true;
        },

        async openTrainingDataFolder() {
            try {
                const result = await this.apiCall('system/open-training-folder', 'POST');
                if (!result.success) {
                    this.showNotification(result.message || '打开文件夹失败', 'error');
                }
            } catch (error) {
                this.showNotification('打开文件夹失败: ' + error.message, 'error');
            }
        },

        async selectExportDir() {
            try {
                let dir = '';
                if (window.pywebview && window.pywebview.api) {
                    dir = await window.pywebview.api.select_folder();
                } else {
                    const result = await this.apiCall('system/select-folder', 'POST');
                    dir = result.path || '';
                }
                if (dir) {
                    this.exportOutputDir = dir;
                }
            } catch (error) {
                console.error('选择目录失败:', error);
            }
        },

        async exportPairs() {
            if (this.selectedPairCount === 0) {
                this.showNotification('请先选择要导出的组', 'warning');
                return;
            }

            this.showNotification('正在导出...', 'info');
            this.showExportDialog = false;
            
            const payload = {
                ids: this.selectedPairIds,
                output_dir: this.exportOutputDir,
                image_format: this.exportImageFormat,
                filename: this.exportFileName,
                naming_mode: this.exportNamingMode,
                suffix_left: this.exportSuffixLeft,
                suffix_left2: this.exportSuffixLeft2,
                suffix_right: this.exportSuffixRight,
                txt_follows: this.exportTxtFollows,
                folder_prefix: this.exportFolderPrefix,
                txt_folder_follows: this.exportTxtFolderFollows,
                unified_file_prefix: this.exportUnifiedFilePrefix,
                runinghub_start: this.exportRuninghubStart,
                runinghub_end: this.exportRuninghubEnd,
                output_type: this.exportOutputType,
                prefix_letter: !!this.exportPrefixLetter
            };

            // 仅当选择“按文件名关键字导出”命名模式时才传 filter 参数
            if (this.exportNamingMode === 'namefilter') {
                payload.filter_keyword = (this.exportFilterKeyword || '').trim();
                const formats = [];
                if (this.exportFilterPNG) formats.push('png');
                if (this.exportFilterJPG) formats.push('jpg');
                if (this.exportFilterTXT) formats.push('txt');
                // fallback to png+txt if nothing selected
                if (formats.length === 0) {
                    formats.push('png', 'txt');
                }
                payload.filter_formats = formats;
            }

            const result = await this.apiCall('pairs/export', 'POST', payload);

            if (result.success) {
                this.showNotification(`${result.message}`, 'success');
                // 弹窗询问是否打开导出文件夹
                this.exportedFilePath = result.file;
                this.showExportSuccessDialog = true;
            }
        },

        async openExportFolder() {
            // 优先使用后端返回的文件夹路径
            const folderPath = this.exportedFolderPath || this.exportedFilePath;
            if (folderPath) {
                await this.apiCall('system/open-folder', 'POST', {
                    path: folderPath
                });
            }
        },

        // 单图打标（获取AI推荐提示词）
        async tagSingleImage(imageId) {
            // 检查是否已有原文标签内容
            const hasExistingText = this.detailImage && this.detailImage.text && this.detailImage.text.trim().length > 0;
            const hasTranslation = this.detailImage && this.detailImage.translatedText && this.detailImage.translatedText.trim().length > 0;
            
            // 如果已有内容，弹出确认框
            if (hasExistingText) {
                const confirmed = await this.confirmAction(
                    '是否覆盖当前结果？',
                    hasTranslation 
                        ? '当前已有原文标签和翻译结果，获取新的AI推荐提示词将覆盖原文标签并自动重新翻译。'
                        : '当前已有原文标签，获取新的AI推荐提示词将覆盖现有内容。'
                );
                
                if (!confirmed) {
                    return; // 用户选择"否"，直接返回
                }
            }
            
            try {
                this.showNotification('正在处理中...', 'info');
                const result = await this.apiCall(`images/tag/${imageId}`, 'POST');
                
                if (result.success) {
                    const index = this.images.findIndex(img => img.id === imageId);
                    if (index !== -1) {
                        this.images[index] = result.image;
                    }
                    if (this.detailImage && this.detailImage.id === imageId) {
                        this.detailImage.text = result.text;
                        
                        // 场景2：如果之前已有翻译结果，自动重新翻译
                        if (hasTranslation) {
                            this.showNotification('正在自动翻译...', 'info');
                            await this.translateDetailImage();
                        }
                    }
                    this.showNotification('反推成功', 'success');
                }
            } catch (error) {
                this.showNotification('反推失败: ' + error.message, 'error');
            }
        },

        // 批量打标
        async batchTag() {
            if (this.selectedCount === 0) {
                this.showNotification('请先选择图片', 'warning');
                return;
            }

            if (!this.apikeyConfig.providers[this.apikeyConfig.current_provider].api_key) {
                this.showNotification('请先配置 API Key', 'warning');
                this.showSettingsModal = true;
                return;
            }

            this.isProcessing = true;
            this.progress = 0;

            const result = await this.apiCall('images/tag', 'POST', {
                ids: this.selectedIds
            });

            if (result.success) {
                const taskId = result.task_id;
                this.currentTaskId = taskId;
                this.showNotification(result.message, 'info');
                
                // 轮询任务状态
                const pollInterval = setInterval(async () => {
                    const statusResult = await this.apiCall(`tasks/${taskId}`);
                    if (statusResult.success) {
                        this.taskStatus = statusResult.task;
                        this.progress = (statusResult.task.completed / statusResult.task.total) * 100;
                        
                        if (statusResult.task.status === 'completed' || statusResult.task.status === 'cancelled') {
                            clearInterval(pollInterval);
                            this.isProcessing = false;
                            this.currentTaskId = null;
                            
                            // 记录失败项
                            if (statusResult.task.failed_ids && statusResult.task.failed_ids.length > 0) {
                                this.lastFailedIds = statusResult.task.failed_ids;
                                this.lastFailedType = 'images';
                            }
                            
                            await this.loadImages();
                            if (statusResult.task.status === 'completed') {
                                if (statusResult.task.failed > 0) {
                                    this.showNotification(`批量处理完成，${statusResult.task.failed} 项失败`, 'warning');
                                } else {
                                    this.showNotification('批量处理完成', 'success');
                                }
                            } else {
                                this.showNotification('已取消批量处理', 'warning');
                            }
                        }
                    }
                }, 1000);
            } else {
                this.isProcessing = false;
                this.currentTaskId = null;
            }
        },

        // 批量反推pairs
        async batchTagPairs() {
            if (this.selectedPairCount === 0) {
                this.showNotification('请先选择要反推的组', 'warning');
                return;
            }

            if (!this.apikeyConfig.providers[this.apikeyConfig.current_provider].api_key) {
                this.showNotification('请先配置 API Key', 'warning');
                this.showSettingsModal = true;
                return;
            }

            this.isProcessing = true;
            this.progress = 0;

            const result = await this.apiCall('pairs/tag', 'POST', {
                ids: this.selectedPairIds
            });

            if (result.success) {
                const taskId = result.task_id;
                this.currentTaskId = taskId;
                this.showNotification(result.message, 'info');
                
                // 轮询任务状态
                const pollInterval = setInterval(async () => {
                    const statusResult = await this.apiCall(`tasks/${taskId}`);
                    if (statusResult.success) {
                        this.taskStatus = statusResult.task;
                        this.progress = (statusResult.task.completed / statusResult.task.total) * 100;
                        
                        if (statusResult.task.status === 'completed' || statusResult.task.status === 'cancelled') {
                            clearInterval(pollInterval);
                            this.isProcessing = false;
                            this.currentTaskId = null;
                            
                            // 记录失败项
                            if (statusResult.task.failed_ids && statusResult.task.failed_ids.length > 0) {
                                this.lastFailedIds = statusResult.task.failed_ids;
                                this.lastFailedType = 'pairs';
                            }
                            
                            await this.loadPairs();
                            if (statusResult.task.status === 'completed') {
                                if (statusResult.task.failed > 0) {
                                    this.showNotification(`批量反推完成，${statusResult.task.failed} 项失败`, 'warning');
                                } else {
                                    this.showNotification('批量反推完成', 'success');
                                }
                            } else {
                                this.showNotification('已取消批量反推', 'warning');
                            }
                        }
                    }
                }, 1000);
            } else {
                this.isProcessing = false;
                this.currentTaskId = null;
            }
        },

        async cancelCurrentTask() {
            if (!this.currentTaskId) return;
            const result = await this.apiCall(`tasks/${this.currentTaskId}/cancel`, 'POST', {});
            if (result.success) {
                this.showNotification(result.message || '已请求取消', 'info');
            }
        },

        // 重试失败的项目
        async retryFailedItems() {
            if (this.lastFailedIds.length === 0) {
                this.showNotification('没有需要重试的项目', 'info');
                return;
            }

            if (!this.apikeyConfig.providers[this.apikeyConfig.current_provider].api_key) {
                this.showNotification('请先配置 API Key', 'warning');
                this.showSettingsModal = true;
                return;
            }

            this.isProcessing = true;
            this.progress = 0;

            const endpoint = this.lastFailedType === 'images' ? 'images/tag' : 'pairs/tag';
            const result = await this.apiCall(endpoint, 'POST', {
                ids: this.lastFailedIds
            });

            if (result.success) {
                const taskId = result.task_id;
                this.currentTaskId = taskId;
                this.showNotification(`正在重试 ${this.lastFailedIds.length} 个失败项...`, 'info');
                
                // 清空失败记录
                const retryType = this.lastFailedType;
                this.lastFailedIds = [];
                this.lastFailedType = '';
                
                // 轮询任务状态
                const pollInterval = setInterval(async () => {
                    const statusResult = await this.apiCall(`tasks/${taskId}`);
                    if (statusResult.success) {
                        this.taskStatus = statusResult.task;
                        this.progress = (statusResult.task.completed / statusResult.task.total) * 100;
                        
                        if (statusResult.task.status === 'completed' || statusResult.task.status === 'cancelled') {
                            clearInterval(pollInterval);
                            this.isProcessing = false;
                            this.currentTaskId = null;
                            
                            // 记录新的失败项
                            if (statusResult.task.failed_ids && statusResult.task.failed_ids.length > 0) {
                                this.lastFailedIds = statusResult.task.failed_ids;
                                this.lastFailedType = retryType;
                            }
                            
                            // 刷新列表
                            if (retryType === 'images') {
                                await this.loadImages();
                            } else {
                                await this.loadPairs();
                            }
                            
                            if (statusResult.task.status === 'completed') {
                                if (statusResult.task.failed > 0) {
                                    this.showNotification(`重试完成，仍有 ${statusResult.task.failed} 项失败`, 'warning');
                                } else {
                                    this.showNotification('重试全部成功', 'success');
                                }
                            } else {
                                this.showNotification('已取消重试', 'warning');
                            }
                        }
                    }
                }, 1000);
            } else {
                this.isProcessing = false;
                this.currentTaskId = null;
            }
        },

        // 开始反推（根据当前模式自动选择）
        async startBatchTag() {
            if (this.modelMode === 'tagging') {
                // 图像反推模式
                if (this.selectedCount > 0) {
                    await this.batchTag();
                } else {
                    this.showNotification('请先选择要反推的图片', 'warning');
                }
            } else if (this.modelMode === 'editing') {
                // 图像编辑模式
                if (this.selectedPairCount > 0) {
                    await this.batchTagPairs();
                } else {
                    this.showNotification('请先选择要反推的图片组', 'warning');
                }
            }
        },

        // 单个pair反推（获取AI推荐提示词）
        async tagSinglePair(pairId) {
            // 检查是否已有原文标签内容
            const hasExistingText = this.detailPair && this.detailPair.text && this.detailPair.text.trim().length > 0;
            const hasTranslation = this.detailPair && this.detailPair.translatedText && this.detailPair.translatedText.trim().length > 0;
            
            // 如果已有内容，弹出确认框
            if (hasExistingText) {
                const confirmed = await this.confirmAction(
                    '是否覆盖当前结果？',
                    hasTranslation 
                        ? '当前已有原文标签和翻译结果，获取新的AI推荐提示词将覆盖原文标签并自动重新翻译。'
                        : '当前已有原文标签，获取新的AI推荐提示词将覆盖现有内容。'
                );
                
                if (!confirmed) {
                    return; // 用户选择"否"，直接返回
                }
            }
            
            try {
                this.showNotification('正在获取AI推荐提示词...', 'info');
                const result = await this.apiCall(`pairs/tag/${pairId}`, 'POST');
                
                if (result.success) {
                    const index = this.pairs.findIndex(p => p.id === pairId);
                    if (index !== -1) {
                        this.pairs[index].text = result.text;
                    }
                    if (this.detailPair && this.detailPair.id === pairId) {
                        this.detailPair.text = result.text;
                        
                        // 场景2：如果之前已有翻译结果，自动重新翻译
                        if (hasTranslation) {
                            this.showNotification('正在自动翻译...', 'info');
                            await this.translateDetailPair();
                        }
                    }
                    this.showNotification('获取成功', 'success');
                }
            } catch (error) {
                this.showNotification('获取失败: ' + error.message, 'error');
            }
        },

        // 翻译pair文本
        async translatePairText() {
            if (!this.detailPair || !this.detailPair.text) {
                this.showNotification('请先输入提示词', 'warning');
                return;
            }
            
            try {
                this.showNotification('正在翻译...', 'info');
                const result = await this.apiCall('translate', 'POST', {
                    text: this.detailPair.text
                });
                
                if (result.success) {
                    this.detailPair.text = result.translated;
                    this.showNotification('翻译成功', 'success');
                }
            } catch (error) {
                this.showNotification('翻译失败: ' + error.message, 'error');
            }
        },

        // 统一翻译函数 - 根据当前模式翻译选中的标签
        async translateSelectedAll() {
            if (this.modelMode === 'tagging') {
                await this.translateSelectedImages();
            } else if (this.modelMode === 'editing') {
                await this.translateSelectedPairs();
            }
        },

        // 翻译选中的图片标签（英文转中文）
        async translateSelectedImages() {
            if (this.selectedIds.length === 0) {
                this.showNotification('请先选择要翻译的图片', 'warning');
                return;
            }
            
            this.isTranslating = true;
            let successCount = 0;
            let failCount = 0;
            
            try {
                for (const imageId of this.selectedIds) {
                    const image = this.images.find(img => img.id === imageId);
                    if (!image || !image.text) continue;
                    
                    try {
                        const result = await this.apiCall('translate', 'POST', {
                            text: image.text,
                            target_lang: 'zh'  // 明确指定翻译为中文
                        });
                        
                        if (result.success) {
                            // 将翻译结果存储到图片对象的 chineseText 属性
                            image.chineseText = result.translated;
                            successCount++;
                        } else {
                            failCount++;
                        }
                    } catch (e) {
                        failCount++;
                    }
                }
                
                if (successCount > 0) {
                    this.showNotification(`已翻译 ${successCount} 个标签`, 'success');
                }
                if (failCount > 0) {
                    this.showNotification(`${failCount} 个标签翻译失败`, 'warning');
                }
            } finally {
                this.isTranslating = false;
            }
        },

        // 将单个图片的中文翻译同步回英文标签
        async syncImageChineseToEnglish(image) {
            if (!image || !image.chineseText) {
                this.showNotification('没有可同步的中文文本', 'warning');
                return;
            }
            
            this.isSyncingTranslation = true;
            try {
                // 将中文翻译回英文（明确指定目标语言为英文）
                const result = await this.apiCall('translate', 'POST', {
                    text: image.chineseText,
                    target_lang: 'en'
                });
                
                if (result.success) {
                    // 更新英文文本
                    image.text = result.translated;
                    // 保存到后端
                    await this.apiCall(`images/${image.id}`, 'PUT', {
                        text: result.translated
                    });
                    this.showNotification('已同步到英文标签', 'success');
                } else {
                    this.showNotification('同步失败: ' + (result.message || '未知错误'), 'error');
                }
            } catch (error) {
                this.showNotification('同步失败: ' + error.message, 'error');
            } finally {
                this.isSyncingTranslation = false;
            }
        },

        // 保存图片的文本（编辑后自动保存）
        async saveImageText(image) {
            if (!image) return;
            try {
                await this.apiCall(`images/${image.id}`, 'PUT', {
                    text: image.text || ''
                });
            } catch (error) {
                console.error('保存文本失败:', error);
            }
        },

        // 翻译选中的图片对标签（英文转中文）- 图像编辑模块
        async translateSelectedPairs() {
            if (this.selectedPairIds.length === 0) {
                this.showNotification('请先选择要翻译的图片对', 'warning');
                return;
            }
            
            this.isTranslating = true;
            let successCount = 0;
            let failCount = 0;
            
            try {
                for (const pairId of this.selectedPairIds) {
                    const pair = this.pairs.find(p => p.id === pairId);
                    if (!pair || !pair.text) continue;
                    
                    try {
                        const result = await this.apiCall('translate', 'POST', {
                            text: pair.text,
                            target_lang: 'zh'  // 明确指定翻译为中文
                        });
                        
                        if (result.success) {
                            // 将翻译结果存储到图片对象的 chineseText 属性
                            pair.chineseText = result.translated;
                            successCount++;
                        } else {
                            failCount++;
                        }
                    } catch (e) {
                        failCount++;
                    }
                }
                
                if (successCount > 0) {
                    this.showNotification(`已翻译 ${successCount} 个标签`, 'success');
                }
                if (failCount > 0) {
                    this.showNotification(`${failCount} 个标签翻译失败`, 'warning');
                }
            } finally {
                this.isTranslating = false;
            }
        },

        // 将单个图片对的中文翻译同步回英文标签
        async syncPairChineseToEnglish(pair) {
            if (!pair || !pair.chineseText) {
                this.showNotification('没有可同步的中文文本', 'warning');
                return;
            }
            
            this.isSyncingTranslation = true;
            try {
                // 将中文翻译回英文（明确指定目标语言为英文）
                const result = await this.apiCall('translate', 'POST', {
                    text: pair.chineseText,
                    target_lang: 'en'
                });
                
                if (result.success) {
                    // 更新英文文本
                    pair.text = result.translated;
                    // 保存到后端
                    await this.apiCall(`pairs/${pair.id}`, 'PUT', {
                        text: result.translated
                    });
                    this.showNotification('已同步到英文标签', 'success');
                } else {
                    this.showNotification('同步失败: ' + (result.message || '未知错误'), 'error');
                }
            } catch (error) {
                this.showNotification('同步失败: ' + error.message, 'error');
            } finally {
                this.isSyncingTranslation = false;
            }
        },

        // 保存pair的文本（编辑后自动保存）
        async savePairText(pair) {
            if (!pair) return;
            try {
                await this.apiCall(`pairs/${pair.id}`, 'PUT', {
                    text: pair.text || ''
                });
            } catch (error) {
                console.error('保存文本失败:', error);
            }
        },

        // 翻译当前选中图片的文本标签（保留兼容）
        async translateCurrentImageText() {
            // 获取当前选中的图片
            let currentText = '';
            
            if (this.modelMode === 'tagging') {
                // 文生图反推模式：获取当前选中或第一张图片的文本
                const selectedImage = this.images.find(img => this.selectedIds.includes(img.id)) || this.images[0];
                if (!selectedImage || !selectedImage.text) {
                    this.showNotification('请先选择有文本的图片', 'warning');
                    return;
                }
                currentText = selectedImage.text;
            } else if (this.modelMode === 'editing') {
                // 图像编辑模式：获取当前详情的文本
                if (!this.detailPair || !this.detailPair.text) {
                    this.showNotification('请先选择有提示词的图片对', 'warning');
                    return;
                }
                currentText = this.detailPair.text;
            }
            
            if (!currentText) {
                this.showNotification('当前没有可翻译的文本', 'warning');
                return;
            }
            
            this.isTranslating = true;
            try {
                const result = await this.apiCall('translate', 'POST', {
                    text: currentText
                });
                
                if (result.success) {
                    this.translatedChineseText = result.translated;
                    this.showNotification('翻译成功', 'success');
                } else {
                    this.showNotification('翻译失败: ' + (result.message || '未知错误'), 'error');
                }
            } catch (error) {
                this.showNotification('翻译失败: ' + error.message, 'error');
            } finally {
                this.isTranslating = false;
            }
        },

        // 将中文翻译同步回英文标签
        async syncChineseToEnglish() {
            if (!this.translatedChineseText) {
                this.showNotification('没有可同步的中文文本', 'warning');
                return;
            }
            
            this.isSyncingTranslation = true;
            try {
                // 将中文翻译回英文
                const result = await this.apiCall('translate', 'POST', {
                    text: this.translatedChineseText
                });
                
                if (result.success) {
                    const englishText = result.translated;
                    
                    // 根据当前模式更新对应的文本
                    if (this.modelMode === 'tagging') {
                        // 更新选中的图片文本
                        const selectedImage = this.images.find(img => this.selectedIds.includes(img.id)) || this.images[0];
                        if (selectedImage) {
                            selectedImage.text = englishText;
                            // 保存到后端
                            await this.apiCall(`images/${selectedImage.id}/text`, 'PUT', {
                                text: englishText
                            });
                        }
                    } else if (this.modelMode === 'editing' && this.detailPair) {
                        // 更新当前详情的文本
                        this.detailPair.text = englishText;
                        // 保存到后端
                        await this.apiCall(`pairs/${this.detailPair.id}/text`, 'PUT', {
                            text: englishText
                        });
                    }
                    
                    this.showNotification('已同步到英文标签', 'success');
                } else {
                    this.showNotification('同步失败: ' + (result.message || '未知错误'), 'error');
                }
            } catch (error) {
                this.showNotification('同步失败: ' + error.message, 'error');
            } finally {
                this.isSyncingTranslation = false;
            }
        },

        // 批量重命名
        async batchRename() {
            const result = await this.apiCall('batch/rename', 'POST', {
                ids: this.selectedIds,
                prefix: this.renamePrefix
            });
            
            if (result.success) {
                // 更新本地图片数据的export_name
                if (result.images) {
                    result.images.forEach(updatedImg => {
                        const index = this.images.findIndex(img => img.id === updatedImg.id);
                        if (index !== -1) {
                            this.images[index].export_name = updatedImg.export_name;
                        }
                    });
                }
                this.showNotification(result.message, 'success');
                this.showRenameDialog = false;
            }
        },

        // 批量添加文本
        async batchAddText() {
            const result = await this.apiCall('batch/add-text', 'POST', {
                ids: this.selectedIds,
                text: this.addTextValue,
                position: 'prefix'
            });
            
            if (result.success) {
                await this.loadImages();
                this.showNotification(result.message, 'success');
                this.showAddTextDialog = false;
            }
        },

        // 批量清空文本
        async clearSelectedText() {
            if (!await this.confirmAction('确认清空', '确定要清空所选图片的文本吗？')) return;
            
            const result = await this.apiCall('batch/clear-text', 'POST', {
                ids: this.selectedIds
            });
            
            if (result.success) {
                await this.loadImages();
                this.showNotification(result.message, 'success');
            }
        },

        // 删除选中的图片
        async deleteSelected() {
            if (!await this.confirmAction('确认删除', `确定要删除所选的 ${this.selectedCount} 张图片吗？\n此操作仅从列表中移除，不会删除源文件。`)) return;

            try {
                const idsToDelete = [...this.selectedIds];
                let successCount = 0;
                let failedCount = 0;

                // 开始进度显示
                this.isProcessing = true;
                this.taskStatus = {
                    total: idsToDelete.length,
                    completed: 0,
                    failed: 0,
                    current_index: 0,
                    current_name: ''
                };

                for (let i = 0; i < idsToDelete.length; i++) {
                    const id = idsToDelete[i];
                    this.taskStatus.current_index = i + 1;
                    this.taskStatus.current_name = `删除图片 ${id}`;

                    try {
                        const result = await this.apiCall(`images/${id}`, 'DELETE');
                        if (result.success) {
                            successCount++;
                        } else {
                            failedCount++;
                        }
                    } catch (error) {
                        console.error(`删除图片 ${id} 失败:`, error);
                        failedCount++;
                    }

                    // 更新进度
                    this.taskStatus.completed = successCount + failedCount;
                    this.taskStatus.failed = failedCount;

                    // 更新进度百分比
                    this.progress = (this.taskStatus.completed / this.taskStatus.total) * 100;
                }

                await this.loadImages();

                // 隐藏进度条
                this.isProcessing = false;
                this.progress = 0;

                if (failedCount === 0) {
                    this.showNotification(`已成功删除 ${successCount} 张图片`, 'success');
                } else {
                    this.showNotification(`删除完成: ${successCount} 成功, ${failedCount} 失败`, failedCount === 0 ? 'success' : 'warning');
                }
            } catch (error) {
                // 隐藏进度条
                this.isProcessing = false;
                this.progress = 0;
                this.showNotification('删除失败: ' + error.message, 'error');
            }
        },

        // 批量裁切
        async batchResize() {
            if (this.selectedIds.length === 0) {
                this.showNotification('请先选择要裁切的图片', 'warning');
                return;
            }
            
            this.showNotification('正在裁切图片...', 'info');
            
            const result = await this.apiCall('batch/resize', 'POST', {
                ids: this.selectedIds,
                max_size: parseInt(this.resizeValue) || 1024
            });
            
            if (result.success) {
                this.showNotification(result.message, 'success');
                this.showResizeDialog = false;
                // 刷新图片列表以更新缩略图和尺寸
                await this.loadImages();
            } else {
                this.showNotification(result.message || '裁切失败', 'error');
            }
        },

        // ==================== 自定义批量裁剪 ====================
        
        // 打开自定义裁剪弹窗
        openCustomCropDialog() {
            if (this.selectedIds.length === 0) {
                this.showNotification('请先选择要裁剪的图片', 'warning');
                return;
            }
            
            // 重置状态
            this.cropUseOriginalRatio = false;
            this.cropLockRatio = true;
            this.cropRatioW = 1;
            this.cropRatioH = 1;
            
            // 获取选中的图片并初始化裁剪框
            const selectedImages = this.images.filter(img => this.selectedIds.includes(img.id));
            const aspectRatio = this.cropTargetWidth / this.cropTargetHeight;
            
            this.cropImages = selectedImages.map(img => {
                // 如果图片已有裁剪参数，使用已有参数
                if (img.crop_params) {
                    // 更新目标尺寸为已有的裁剪尺寸（使用第一张图片的参数）
                    if (this.cropImages.length === 0) {
                        this.cropTargetWidth = img.crop_params.target_width;
                        this.cropTargetHeight = img.crop_params.target_height;
                    }
                    return {
                        id: img.id,
                        name: img.name || img.export_name,
                        thumbnail: img.original_thumbnail || img.thumbnail,
                        width: img.width,
                        height: img.height,
                        cropX: img.crop_params.crop_x,
                        cropY: img.crop_params.crop_y,
                        cropWidth: img.crop_params.crop_width,
                        cropHeight: img.crop_params.crop_height,
                        targetWidth: img.crop_params.target_width,
                        targetHeight: img.crop_params.target_height,
                        scale: img.crop_params.image_scale || 1,  // 图片缩放比例
                        offsetX: img.crop_params.offset_x || 0,   // 图片X偏移
                        offsetY: img.crop_params.offset_y || 0    // 图片Y偏移
                    };
                }
                
                // 计算初始裁剪框（居中，保持目标比例）
                const imgAspect = img.width / img.height;
                let cropWidth, cropHeight;
                
                if (imgAspect > aspectRatio) {
                    // 图片更宽，以高度为基准
                    cropHeight = 1;
                    cropWidth = aspectRatio / imgAspect;
                } else {
                    // 图片更高，以宽度为基准
                    cropWidth = 1;
                    cropHeight = imgAspect / aspectRatio;
                }
                
                return {
                    id: img.id,
                    name: img.name || img.export_name,
                    thumbnail: img.original_thumbnail || img.thumbnail,
                    width: img.width,
                    height: img.height,
                    cropX: (1 - cropWidth) / 2,
                    cropY: (1 - cropHeight) / 2,
                    cropWidth: cropWidth,
                    cropHeight: cropHeight,
                    targetWidth: null,  // 使用全局设置
                    targetHeight: null,
                    scale: 1,  // 图片缩放比例，默认1，最小0.5
                    offsetX: 0,  // 缩小图片时的X偏移（-0.5到0.5）
                    offsetY: 0   // 缩小图片时的Y偏移（-0.5到0.5）
                };
            });
            
            this.showCustomCropDialog = true;
        },
        
        // 检查图片是否被缩小
        isImageScaled(cropImg) {
            return cropImg.scale < 1;
        },
        
        // 双击重置图片到原始裁切位置
        resetCropImage(index) {
            const img = this.cropImages[index];
            const aspectRatio = this.cropTargetWidth / this.cropTargetHeight;
            const imgAspect = img.width / img.height;
            
            // 重置缩放比例和偏移
            img.scale = 1;
            img.offsetX = 0;
            img.offsetY = 0;
            
            if (this.cropUseOriginalRatio) {
                // 原图比例模式：裁剪框覆盖整个图片
                img.cropX = 0;
                img.cropY = 0;
                img.cropWidth = 1;
                img.cropHeight = 1;
            } else {
                // 固定比例模式：计算最大裁剪框并居中
                let cropWidth, cropHeight;
                
                if (imgAspect > aspectRatio) {
                    cropHeight = 1;
                    cropWidth = aspectRatio / imgAspect;
                } else {
                    cropWidth = 1;
                    cropHeight = imgAspect / aspectRatio;
                }
                
                img.cropX = (1 - cropWidth) / 2;
                img.cropY = (1 - cropHeight) / 2;
                img.cropWidth = cropWidth;
                img.cropHeight = cropHeight;
            }
        },
        
        // 获取缩小图片的样式（用于 scale < 1 时的预览）
        // 预览框此时使用目标比例，图片需要按 contain 模式缩放后再按 scale 缩小
        getScaledImageStyle(cropImg) {
            const scale = cropImg.scale || 1;
            const offsetX = cropImg.offsetX || 0;
            const offsetY = cropImg.offsetY || 0;
            
            // 计算图片在目标比例画布中的 contain 尺寸
            const imgAspect = cropImg.width / cropImg.height;
            const targetAspect = this.cropTargetWidth / this.cropTargetHeight;
            
            let imgWidthPercent, imgHeightPercent;
            if (imgAspect > targetAspect) {
                // 图片更宽，以宽度为基准
                imgWidthPercent = 100;
                imgHeightPercent = 100 * targetAspect / imgAspect;
            } else {
                // 图片更高，以高度为基准
                imgHeightPercent = 100;
                imgWidthPercent = 100 * imgAspect / targetAspect;
            }
            
            // 按 scale 缩小
            const scaledWidth = imgWidthPercent * scale;
            const scaledHeight = imgHeightPercent * scale;
            
            // 计算位置（居中 + 偏移）
            // 基础位置（居中）
            const baseLeft = (100 - scaledWidth) / 2;
            const baseTop = (100 - scaledHeight) / 2;
            
            // 偏移量：offsetX/Y 的范围是 [-(1-scale)/2, (1-scale)/2]
            // 需要转换为百分比
            const maxOffset = (1 - scale) / 2;
            const offsetXPercent = maxOffset > 0 ? (offsetX / maxOffset) * baseLeft : 0;
            const offsetYPercent = maxOffset > 0 ? (offsetY / maxOffset) * baseTop : 0;
            
            const left = baseLeft + offsetXPercent;
            const top = baseTop + offsetYPercent;
            
            return `width: ${scaledWidth}%; height: ${scaledHeight}%; left: ${left}%; top: ${top}%;`;
        },
        
        // 关闭自定义裁剪弹窗
        closeCustomCropDialog() {
            this.showCustomCropDialog = false;
            this.cropImages = [];
            this.cropDragState = null;
        },
        
        // 设置裁剪尺寸
        setCropSize(width, height) {
            this.cropTargetWidth = width;
            this.cropTargetHeight = height;
            this.cropRatioW = width;
            this.cropRatioH = height;
            // 简化比例
            const gcd = this.getGCD(width, height);
            this.cropRatioW = width / gcd;
            this.cropRatioH = height / gcd;
            this.onCropSizeChange();
        },
        
        // 设置裁剪比例
        setCropRatio(ratioW, ratioH) {
            this.cropRatioW = ratioW;
            this.cropRatioH = ratioH;
            if (this.cropLockRatio) {
                // 保持宽度，调整高度
                this.cropTargetHeight = Math.round(this.cropTargetWidth * ratioH / ratioW);
            }
            this.onCropSizeChange();
        },
        
        // 自定义比例变化
        onCustomRatioChange() {
            if (this.cropRatioW > 0 && this.cropRatioH > 0 && this.cropLockRatio) {
                this.cropTargetHeight = Math.round(this.cropTargetWidth * this.cropRatioH / this.cropRatioW);
                this.onCropSizeChange();
            }
        },
        
        // 交换宽高比例
        swapCropRatio() {
            const temp = this.cropRatioW;
            this.cropRatioW = this.cropRatioH;
            this.cropRatioH = temp;
            // 同时交换目标尺寸
            const tempSize = this.cropTargetWidth;
            this.cropTargetWidth = this.cropTargetHeight;
            this.cropTargetHeight = tempSize;
            this.onCropSizeChange();
        },
        
        // 宽度变化时
        onCropWidthChange() {
            if (this.cropLockRatio && this.cropRatioW > 0 && this.cropRatioH > 0) {
                this.cropTargetHeight = Math.round(this.cropTargetWidth * this.cropRatioH / this.cropRatioW);
            }
            this.onCropSizeChange();
        },
        
        // 高度变化时
        onCropHeightChange() {
            if (this.cropLockRatio && this.cropRatioW > 0 && this.cropRatioH > 0) {
                this.cropTargetWidth = Math.round(this.cropTargetHeight * this.cropRatioW / this.cropRatioH);
            }
            this.onCropSizeChange();
        },
        
        // 原图比例模式变化
        onCropOriginalRatioChange() {
            if (this.cropUseOriginalRatio) {
                // 每张图片使用自己的原图比例
                this.cropImages = this.cropImages.map(img => {
                    const imgAspect = img.width / img.height;
                    let targetWidth, targetHeight;
                    
                    if (img.width >= img.height) {
                        targetWidth = this.cropOriginalMaxSize;
                        targetHeight = Math.round(this.cropOriginalMaxSize / imgAspect);
                    } else {
                        targetHeight = this.cropOriginalMaxSize;
                        targetWidth = Math.round(this.cropOriginalMaxSize * imgAspect);
                    }
                    
                    return {
                        ...img,
                        cropX: 0,
                        cropY: 0,
                        cropWidth: 1,
                        cropHeight: 1,
                        targetWidth: targetWidth,
                        targetHeight: targetHeight,
                        scale: 1,  // 重置缩放
                        offsetX: 0,  // 重置偏移
                        offsetY: 0
                    };
                });
            } else {
                // 恢复统一比例模式
                this.onCropSizeChange();
            }
        },
        
        // 求最大公约数
        getGCD(a, b) {
            a = Math.abs(Math.round(a));
            b = Math.abs(Math.round(b));
            while (b) {
                const t = b;
                b = a % b;
                a = t;
            }
            return a || 1;
        },
        
        // 裁剪尺寸变化时更新所有裁剪框
        onCropSizeChange() {
            if (this.cropUseOriginalRatio) return;
            
            const aspectRatio = this.cropTargetWidth / this.cropTargetHeight;
            
            this.cropImages = this.cropImages.map(img => {
                const imgAspect = img.width / img.height;
                let cropWidth, cropHeight;
                
                if (imgAspect > aspectRatio) {
                    cropHeight = 1;
                    cropWidth = aspectRatio / imgAspect;
                } else {
                    cropWidth = 1;
                    cropHeight = imgAspect / aspectRatio;
                }
                
                // 保持裁剪框居中，重置缩放
                return {
                    ...img,
                    cropX: (1 - cropWidth) / 2,
                    cropY: (1 - cropHeight) / 2,
                    cropWidth: cropWidth,
                    cropHeight: cropHeight,
                    targetWidth: null,
                    targetHeight: null,
                    scale: 1,  // 重置缩放
                    offsetX: 0,  // 重置偏移
                    offsetY: 0
                };
            });
        },
        
        // 重置所有裁剪框
        resetAllCropBoxes() {
            if (this.cropUseOriginalRatio) {
                this.onCropOriginalRatioChange();
            } else {
                this.onCropSizeChange();
            }
        },
        
        // 鼠标滚轮缩放裁剪框
        onCropWheel(event, index) {
            const img = this.cropImages[index];
            
            // 初始化 scale 如果不存在
            if (img.scale === undefined) img.scale = 1;
            
            // 原图比例模式下，滚轮调整整体缩放
            if (this.cropUseOriginalRatio) {
                // 滚轮调整裁剪框大小（保持原图比例）
                const delta = event.deltaY > 0 ? 0.95 : 1.05;
                let newWidth = img.cropWidth * delta;
                let newHeight = img.cropHeight * delta;
                
                // 限制范围
                if (newWidth > 1) newWidth = 1;
                if (newHeight > 1) newHeight = 1;
                if (newWidth < 0.1) newWidth = 0.1;
                if (newHeight < 0.1) newHeight = 0.1;
                
                // 保持中心位置
                const centerX = img.cropX + img.cropWidth / 2;
                const centerY = img.cropY + img.cropHeight / 2;
                let newX = centerX - newWidth / 2;
                let newY = centerY - newHeight / 2;
                
                // 边界检查
                newX = Math.max(0, Math.min(newX, 1 - newWidth));
                newY = Math.max(0, Math.min(newY, 1 - newHeight));
                
                img.cropX = newX;
                img.cropY = newY;
                img.cropWidth = newWidth;
                img.cropHeight = newHeight;
                return;
            }
            
            const aspectRatio = this.cropTargetWidth / this.cropTargetHeight;
            const imgAspect = img.width / img.height;
            const targetCropAspect = aspectRatio / imgAspect;
            
            // 计算当前裁剪框是否已经达到最大（覆盖整个图片）
            const isAtMaxCrop = (img.cropWidth >= 0.99 || img.cropHeight >= 0.99);
            
            // 向下滚动 = 放大裁剪框（或缩小图片），向上滚动 = 缩小裁剪框（或放大图片）
            const isZoomingIn = event.deltaY > 0;  // 放大裁剪框
            
            if (isZoomingIn && isAtMaxCrop && img.scale > 0.5) {
                // 裁剪框已最大，通过缩小图片来实现"放大"效果
                const scaleDelta = 0.95;
                let newScale = img.scale * scaleDelta;
                newScale = Math.max(0.5, newScale);  // 最小缩小到50%
                img.scale = newScale;
                return;
            } else if (!isZoomingIn && img.scale < 1) {
                // 图片被缩小了，先恢复图片大小
                const scaleDelta = 1.05;
                let newScale = img.scale * scaleDelta;
                newScale = Math.min(1, newScale);  // 最大恢复到100%
                img.scale = newScale;
                // 当 scale 恢复到 1 时，重置 offset
                if (newScale >= 1) {
                    img.offsetX = 0;
                    img.offsetY = 0;
                }
                return;
            }
            
            // 正常的裁剪框缩放
            const delta = event.deltaY > 0 ? 1.05 : 0.95;  // 向下滚动放大裁剪框，向上滚动缩小
            
            let newWidth = img.cropWidth * delta;
            let newHeight = img.cropHeight * delta;
            
            // 保持比例
            if (newWidth / newHeight > targetCropAspect) {
                newWidth = newHeight * targetCropAspect;
            } else {
                newHeight = newWidth / targetCropAspect;
            }
            
            // 限制最小尺寸
            if (newWidth < 0.1 || newHeight < 0.1) return;
            
            // 限制最大尺寸（不超出图片边界）
            if (newWidth > 1 || newHeight > 1) {
                if (imgAspect > aspectRatio) {
                    newHeight = 1;
                    newWidth = targetCropAspect;
                } else {
                    newWidth = 1;
                    newHeight = 1 / targetCropAspect;
                }
            }
            
            // 保持裁剪框中心位置不变
            const centerX = img.cropX + img.cropWidth / 2;
            const centerY = img.cropY + img.cropHeight / 2;
            
            let newX = centerX - newWidth / 2;
            let newY = centerY - newHeight / 2;
            
            // 确保不超出边界
            newX = Math.max(0, Math.min(newX, 1 - newWidth));
            newY = Math.max(0, Math.min(newY, 1 - newHeight));
            
            img.cropX = newX;
            img.cropY = newY;
            img.cropWidth = newWidth;
            img.cropHeight = newHeight;
        },
        
        // 开始拖动裁剪框
        startCropDrag(event, index) {
            if (this.cropDragState) return;
            
            const rect = event.currentTarget.getBoundingClientRect();
            const x = (event.clientX - rect.left) / rect.width;
            const y = (event.clientY - rect.top) / rect.height;
            
            const img = this.cropImages[index];
            
            // 如果图片被缩小（scale < 1），直接拖动图片
            if ((img.scale || 1) < 1) {
                this.cropDragState = {
                    index,
                    startX: event.clientX,
                    startY: event.clientY,
                    startOffsetX: img.offsetX || 0,
                    startOffsetY: img.offsetY || 0,
                    type: 'moveImage',
                    rect
                };
                return;
            }
            
            // 检查是否在裁剪框内
            if (x >= img.cropX && x <= img.cropX + img.cropWidth &&
                y >= img.cropY && y <= img.cropY + img.cropHeight) {
                this.cropDragState = {
                    index,
                    startX: event.clientX,
                    startY: event.clientY,
                    startCropX: img.cropX,
                    startCropY: img.cropY,
                    type: 'move',
                    rect
                };
            }
        },
        
        // 开始调整裁剪框大小
        startCropResize(event, index, corner) {
            const rect = event.currentTarget.closest('.relative').getBoundingClientRect();
            const img = this.cropImages[index];
            
            this.cropDragState = {
                index,
                startX: event.clientX,
                startY: event.clientY,
                startCropX: img.cropX,
                startCropY: img.cropY,
                startCropWidth: img.cropWidth,
                startCropHeight: img.cropHeight,
                type: 'resize',
                corner,
                rect
            };
            
            // 添加全局事件监听
            document.addEventListener('mousemove', this.handleGlobalCropDrag);
            document.addEventListener('mouseup', this.handleGlobalCropDragEnd);
        },
        
        // 处理裁剪框拖动
        onCropDrag(event, index) {
            if (!this.cropDragState || this.cropDragState.index !== index) return;
            
            const state = this.cropDragState;
            const rect = event.currentTarget.getBoundingClientRect();
            const img = this.cropImages[index];
            const aspectRatio = this.cropTargetWidth / this.cropTargetHeight;
            const imgAspect = img.width / img.height;
            
            if (state.type === 'move') {
                // 移动裁剪框
                const deltaX = (event.clientX - state.startX) / rect.width;
                const deltaY = (event.clientY - state.startY) / rect.height;
                
                let newX = state.startCropX + deltaX;
                let newY = state.startCropY + deltaY;
                
                // 限制在图片范围内
                newX = Math.max(0, Math.min(newX, 1 - img.cropWidth));
                newY = Math.max(0, Math.min(newY, 1 - img.cropHeight));
                
                img.cropX = newX;
                img.cropY = newY;
            } else if (state.type === 'moveImage') {
                // 移动缩小的图片
                const deltaX = (event.clientX - state.startX) / rect.width;
                const deltaY = (event.clientY - state.startY) / rect.height;
                
                let newOffsetX = state.startOffsetX + deltaX;
                let newOffsetY = state.startOffsetY + deltaY;
                
                // 限制偏移范围（图片不能完全移出画布）
                const maxOffset = (1 - (img.scale || 1)) / 2;
                newOffsetX = Math.max(-maxOffset, Math.min(newOffsetX, maxOffset));
                newOffsetY = Math.max(-maxOffset, Math.min(newOffsetY, maxOffset));
                
                img.offsetX = newOffsetX;
                img.offsetY = newOffsetY;
            }
        },
        
        // 全局拖动处理（用于resize）
        handleGlobalCropDrag(event) {
            if (!this.cropDragState || this.cropDragState.type !== 'resize') return;
            
            const state = this.cropDragState;
            const img = this.cropImages[state.index];
            const rect = state.rect;
            const aspectRatio = this.cropTargetWidth / this.cropTargetHeight;
            const imgAspect = img.width / img.height;
            
            const deltaX = (event.clientX - state.startX) / rect.width;
            const deltaY = (event.clientY - state.startY) / rect.height;
            
            // 根据角落调整大小（保持比例）
            let newWidth = state.startCropWidth;
            let newHeight = state.startCropHeight;
            let newX = state.startCropX;
            let newY = state.startCropY;
            
            // 计算基于拖动方向的缩放
            let scale = 1;
            if (state.corner === 'se') {
                scale = Math.max(deltaX / state.startCropWidth, deltaY / state.startCropHeight) + 1;
            } else if (state.corner === 'nw') {
                scale = Math.max(-deltaX / state.startCropWidth, -deltaY / state.startCropHeight) + 1;
                scale = 2 - scale;  // 反向
            } else if (state.corner === 'ne') {
                scale = Math.max(deltaX / state.startCropWidth, -deltaY / state.startCropHeight) + 1;
            } else if (state.corner === 'sw') {
                scale = Math.max(-deltaX / state.startCropWidth, deltaY / state.startCropHeight) + 1;
                scale = 2 - scale;  // 反向
            }
            
            scale = Math.max(0.1, Math.min(scale, 3));  // 限制缩放范围
            
            newWidth = state.startCropWidth * scale;
            newHeight = state.startCropHeight * scale;
            
            // 根据角落调整位置
            if (state.corner === 'nw') {
                newX = state.startCropX + state.startCropWidth - newWidth;
                newY = state.startCropY + state.startCropHeight - newHeight;
            } else if (state.corner === 'ne') {
                newY = state.startCropY + state.startCropHeight - newHeight;
            } else if (state.corner === 'sw') {
                newX = state.startCropX + state.startCropWidth - newWidth;
            }
            
            // 限制在图片范围内
            if (newX < 0) {
                newWidth += newX;
                newX = 0;
            }
            if (newY < 0) {
                newHeight += newY;
                newY = 0;
            }
            if (newX + newWidth > 1) {
                newWidth = 1 - newX;
            }
            if (newY + newHeight > 1) {
                newHeight = 1 - newY;
            }
            
            // 保持比例
            const targetCropAspect = aspectRatio / imgAspect;
            if (newWidth / newHeight > targetCropAspect) {
                newWidth = newHeight * targetCropAspect;
            } else {
                newHeight = newWidth / targetCropAspect;
            }
            
            // 确保最小尺寸
            if (newWidth >= 0.05 && newHeight >= 0.05) {
                img.cropX = newX;
                img.cropY = newY;
                img.cropWidth = newWidth;
                img.cropHeight = newHeight;
            }
        },
        
        // 全局拖动结束
        handleGlobalCropDragEnd() {
            document.removeEventListener('mousemove', this.handleGlobalCropDrag);
            document.removeEventListener('mouseup', this.handleGlobalCropDragEnd);
            this.cropDragState = null;
        },
        
        // 结束拖动
        endCropDrag(event) {
            if (this.cropDragState && (this.cropDragState.type === 'move' || this.cropDragState.type === 'moveImage')) {
                this.cropDragState = null;
            }
        },
        
        // 确认裁剪
        async confirmCustomCrop() {
            if (this.cropImages.length === 0) return;
            
            this.isCropping = true;
            this.showNotification('正在裁剪图片...', 'info');
            
            try {
                const cropData = this.cropImages.map(img => ({
                    id: img.id,
                    crop_x: img.cropX,
                    crop_y: img.cropY,
                    crop_width: img.cropWidth,
                    crop_height: img.cropHeight,
                    // 如果图片有独立的目标尺寸，使用独立尺寸；否则使用全局设置
                    target_width: img.targetWidth || this.cropTargetWidth,
                    target_height: img.targetHeight || this.cropTargetHeight,
                    image_scale: img.scale || 1,  // 图片缩放比例
                    offset_x: img.offsetX || 0,   // 图片X偏移
                    offset_y: img.offsetY || 0    // 图片Y偏移
                }));
                
                // 使用新的API，支持每张图片独立尺寸
                const result = await this.apiCall('batch/crop-individual', 'POST', {
                    crop_data: cropData,
                    fill_background: this.cropFillBackground,
                    background_color: this.cropBackgroundColor
                });
                
                if (result.success) {
                    this.showNotification(result.message, 'success');
                    // 先关闭弹窗
                    this.showCustomCropDialog = false;
                    this.cropImages = [];
                    this.cropDragState = null;
                    this.isCropping = false;
                    // 刷新图片列表
                    await this.loadImages();
                } else {
                    this.showNotification(result.message || '裁剪失败', 'error');
                    this.isCropping = false;
                }
            } catch (error) {
                this.showNotification('裁剪失败: ' + error.message, 'error');
                this.isCropping = false;
            }
        },
        
        // 重置选中图片的裁剪
        async resetSelectedCrop() {
            if (this.selectedIds.length === 0) {
                this.showNotification('请先选择要重置的图片', 'warning');
                return;
            }
            
            // 检查是否有裁剪过的图片
            const croppedImages = this.images.filter(img => 
                this.selectedIds.includes(img.id) && img.crop_params
            );
            
            if (croppedImages.length === 0) {
                this.showNotification('选中的图片没有裁剪记录', 'info');
                return;
            }
            
            this.showNotification('正在重置裁剪...', 'info');
            
            try {
                const result = await this.apiCall('batch/reset-crop', 'POST', {
                    ids: this.selectedIds
                });
                
                if (result.success) {
                    this.showNotification(result.message, 'success');
                    // 刷新图片列表
                    await this.loadImages();
                } else {
                    this.showNotification(result.message || '重置失败', 'error');
                }
            } catch (error) {
                this.showNotification('重置失败: ' + error.message, 'error');
            }
        },

        // 导出数据集
        async exportDataset() {
            if (this.selectedCount === 0) {
                alert('请先选择要导出的图片');
                return;
            }
            
            // 打开导出对话框
            this.showImageExportDialog = true;
        },
        
        // 浏览选择导出路径
        async browseImageExportPath() {
            try {
                const result = await this.apiCall('system/select-folder', 'POST', {});
                if (result.success && result.path) {
                    // 无论 ZIP 还是文件夹模式，都直接使用选择的路径
                    this.imageExportPath = result.path;
                }
            } catch (e) {
                console.error('选择文件夹失败:', e);
            }
        },
        
        // 确认导出
        async confirmImageExport() {
            if (this.selectedCount === 0) {
                alert('请先选择要导出的图片');
                return;
            }
            
            this.showImageExportDialog = false;
            
            const result = await this.apiCall('export', 'POST', {
                ids: this.selectedIds,
                format: this.imageExportFormat,
                output_type: this.imageExportOutputType,
                output_path: this.imageExportPath.trim()
            });
            
            if (result.success) {
                this.exportedFilePath = result.file;
                this.exportedFolderPath = result.folder || '';  // 保存文件夹路径
                this.showExportSuccessDialog = true;
            } else {
                alert('导出失败: ' + (result.message || '未知错误'));
            }
        },

        // 通知提示（已禁用）
        showNotification(message, type = 'info') {
            // 全局禁用通知：不执行任何 UI 操作
            return;
        },

        // 移除通知（已禁用）
        removeNotification(id) {
            // 不做任何处理
            return;
        },

        // 确认对话框操作
        confirmAction(title, message) {
            // 优先使用原生 window.confirm 以兼容已移除自定义确认弹窗的情况
            try {
                const confirmed = window.confirm((title ? title + '\\n' : '') + (message || ''));
                return Promise.resolve(!!confirmed);
            } catch (e) {
                // 回退到原有的自定义确认对话框行为（如果存在）
                return new Promise((resolve) => {
                    this.confirmTitle = title;
                    this.confirmMessage = message;
                    this.confirmCallback = resolve;
                    this.showConfirmDialog = true;
                });
            }
        },

        handleConfirm(result) {
            this.showConfirmDialog = false;
            if (this.confirmCallback) {
                this.confirmCallback(result);
                this.confirmCallback = null;
            }
        },

        // ==================== 训练分析器方法 ====================
        
        // 加载训练分析器设置
        async loadAnalyzerSettings() {
            const result = await this.apiCall('analyzer/settings');
            if (result.success && result.settings) {
                this.analyzerSystemPrompt = result.settings.system_prompt || this.getDefaultAnalyzerSystemPrompt();
                this.analyzerUserPrompt = result.settings.user_prompt || '';
            } else {
                // 使用默认值
                this.analyzerSystemPrompt = this.getDefaultAnalyzerSystemPrompt();
                this.analyzerUserPrompt = '';
            }
        },

        // 获取默认的训练分析器系统提示词
        getDefaultAnalyzerSystemPrompt() {
            return `你是一位专业的深度学习训练专家。请根据提供的训练日志数据，分析训练过程并给出专业的优化建议。

分析时请关注以下方面：
1. **训练收敛性分析**：Loss曲线是否平稳下降，是否存在震荡或过拟合迹象
2. **最优Epoch判断**：根据val_loss确定最佳保存点
3. **学习率建议**：根据Loss变化趋势判断学习率是否合适
4. **训练轮数建议**：是否需要更多epoch或提前停止
5. **其他优化建议**：如数据增强、正则化、batch size调整等

请用中文回答，格式清晰，使用Markdown格式输出。`;
        },

        // 保存训练分析器设置
        async saveAnalyzerSettings() {
            const result = await this.apiCall('analyzer/settings', 'POST', {
                system_prompt: this.analyzerSystemPrompt,
                user_prompt: this.analyzerUserPrompt
            });
            
            if (result.success) {
                this.showNotification('✅ 训练分析器设置已保存', 'success');
                this.showAnalyzerSettingsModal = false;
            } else {
                this.showNotification('❌ 保存失败: ' + (result.message || '未知错误'), 'error');
            }
        },

        // 恢复默认提示词
        resetAnalyzerPrompts() {
            this.analyzerSystemPrompt = this.getDefaultAnalyzerSystemPrompt();
            this.analyzerUserPrompt = '';
            this.showNotification('已恢复默认提示词', 'info');
        },
        
        // 加载待分析文件列表
        async loadPendingLogs() {
            const result = await this.apiCall('analyzer/pending-logs');
            if (result.success) {
                this.pendingLogs = result.files || [];
            }
        },

        // 处理拖拽上传
        handleDragOver(e) {
            e.preventDefault();
            this.isDragOver = true;
        },

        handleDragLeave(e) {
            e.preventDefault();
            this.isDragOver = false;
        },

        async handleDrop(e) {
            e.preventDefault();
            this.isDragOver = false;
            
            const files = e.dataTransfer.files;
            for (const file of files) {
                if (file.name.endsWith('.txt') || file.name.endsWith('.log')) {
                    await this.uploadLogFile(file);
                }
            }
        },

        // 上传日志文件
        async uploadLogFile(file) {
            const formData = new FormData();
            formData.append('file', file);
            
            try {
                const response = await fetch('/api/analyzer/upload', {
                    method: 'POST',
                    body: formData
                });
                const result = await response.json();
                
                if (result.success) {
                    this.showNotification(`已添加: ${result.name}`, 'success');
                    await this.loadPendingLogs();
                } else {
                    this.showNotification('上传失败: ' + result.message, 'error');
                }
            } catch (error) {
                this.showNotification('上传失败: ' + error.message, 'error');
            }
        },

        // 从路径添加日志文件
        async addLogFromPath(path) {
            const result = await this.apiCall('analyzer/upload', 'POST', { path });
            if (result.success) {
                this.showNotification(`已添加: ${result.name}`, 'success');
                await this.loadPendingLogs();
            }
        },

        // 分析并移动到历史
        async analyzeAndMove(logPath) {
            this.showNotification('正在分析...', 'info');
            
            const result = await this.apiCall('analyzer/analyze-and-move', 'POST', {
                path: logPath
            });

            if (result.success) {
                this.analyzerResult = result.result;
                this.currentSessionIndex = 0;
                this.updateCurrentStats();
                
                const sessions = result.result.training_sessions || [];
                if (sessions.length > 1) {
                    this.showNotification(`分析完成！发现 ${sessions.length} 个训练任务，已移动到历史目录`, 'success');
                } else {
                    const stats = result.result.statistics || sessions[0]?.statistics;
                    if (stats) {
                        this.showNotification(`分析完成！最佳Loss: ${stats.min_loss.toFixed(6)} (Epoch ${stats.best_epoch})`, 'success');
                    }
                }
                
                await this.loadPendingLogs();
                await this.loadAnalyzerRecords();
                
                // 尝试获取训练集数量并写入 config.dataset_count
                try {
                    const cfg = this.analyzerResult.config || (this.analyzerResult.training_sessions && this.analyzerResult.training_sessions[0] && this.analyzerResult.training_sessions[0].config) || {};
                    const trainDir = cfg.train_data_dir;
                    if (trainDir) {
                        const res = await this.apiCall('analyzer/count-files', 'POST', { path: trainDir });
                        if (res && res.success) {
                            if (this.analyzerResult.config) this.analyzerResult.config.dataset_count = res.count;
                            if (this.analyzerResult.training_sessions && this.analyzerResult.training_sessions[0]) this.analyzerResult.training_sessions[0].config.dataset_count = res.count;
                        }
                    }
                } catch (e) {
                    console.debug('获取训练集数量失败', e);
                }

                // 切换到曲线标签页并绘制图表
                this.analyzerSubTab = 'curve';
                setTimeout(() => this.drawCharts(), 100);
            }
        },

        // 分析所有待处理文件
        async analyzeAllPending() {
            if (this.pendingLogs.length === 0) {
                this.showNotification('没有待分析的文件', 'warning');
                return;
            }
            
            for (const log of this.pendingLogs) {
                await this.analyzeAndMove(log.path);
            }
        },

        // 删除待分析文件
        async deletePendingLog(logPath) {
            if (!await this.confirmAction('确认删除', '确定要删除这个文件吗？')) return;
            
            const result = await this.apiCall('analyzer/delete-pending', 'POST', {
                path: logPath
            });
            
            if (result.success) {
                this.showNotification('文件已删除', 'success');
                await this.loadPendingLogs();
            }
        },

        // 格式化文件大小
        formatFileSize(bytes) {
            if (bytes < 1024) return bytes + ' B';
            if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
            return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
        },

        // AI分析训练数据
        async aiAnalyzeTraining() {
            if (!this.analyzerResult) {
                this.showNotification('请先分析日志文件', 'warning');
                return;
            }
            
            if (!this.apiKey) {
                this.showNotification('请先在设置中配置API密钥', 'warning');
                return;
            }
            
            this.isAiAnalyzing = true;
            this.aiAnalysisResult = '';
            this.showNotification('AI正在分析训练数据...', 'info');
            
            try {
                // 获取当前训练数据
                let trainingData = {};
                if (this.analyzerResult.training_sessions && this.analyzerResult.training_sessions.length > 0) {
                    const session = this.analyzerResult.training_sessions[this.currentSessionIndex] || this.analyzerResult.training_sessions[0];
                    trainingData = {
                        statistics: session.statistics,
                        config: session.config,
                        val_losses: session.val_losses
                    };
                } else {
                    trainingData = {
                        statistics: this.analyzerResult.statistics,
                        config: this.analyzerResult.config,
                        val_losses: this.analyzerResult.val_losses
                    };
                }
                
                // 获取系统提示词和用户提示词（使用训练分析器专用设置）
                const systemPrompt = this.analyzerSystemPrompt || this.getDefaultAnalyzerSystemPrompt();
                const userPrompt = this.analyzerUserPrompt || '';
                
                const result = await this.apiCall('analyzer/ai-analyze', 'POST', {
                    training_data: trainingData,
                    api_key: this.apiKey,
                    base_url: this.baseUrl,
                    model: this.apikeyConfig.model,
                    system_prompt: systemPrompt,
                    user_prompt: userPrompt
                });
                
                if (result.success) {
                    this.aiAnalysisResult = result.analysis;
                    this.showNotification('AI分析完成！', 'success');
                } else {
                    this.showNotification('AI分析失败: ' + result.message, 'error');
                }
            } catch (error) {
                this.showNotification('AI分析失败: ' + error.message, 'error');
            } finally {
                this.isAiAnalyzing = false;
            }
        },

        // 浏览日志文件
        async browseLogFile() {
            try {
                if (window.pywebview && window.pywebview.api) {
                    // 桌面环境使用原生对话框，传入 'log' 过滤器
                    const paths = await window.pywebview.api.select_files('log');
                    if (paths && paths.length > 0) {
                        this.analyzerLogPath = paths[0];
                    }
                } else {
                    // 浏览器模式：使用后端 API 调用系统对话框
                    const result = await this.apiCall('system/select-files', 'POST', {
                        type: 'log',
                        multiple: false
                    });
                    
                    if (result.success && result.paths && result.paths.length > 0) {
                        this.analyzerLogPath = result.paths[0];
                    }
                }
            } catch (error) {
                this.showNotification('文件选择失败: ' + error.message, 'error');
            }
        },

        // 分析日志
        async analyzeLog() {
            if (!this.analyzerLogPath) {
                this.showNotification('请先选择日志文件', 'warning');
                return;
            }

            this.showNotification('正在分析日志...', 'info');
            
            const result = await this.apiCall('analyzer/parse', 'POST', {
                path: this.analyzerLogPath
            });

            if (result.success) {
                this.analyzerResult = result;
                this.currentSessionIndex = 0;
                this.updateCurrentStats();
                
                // 延迟绘制图表，等待 DOM 更新
                setTimeout(() => {
                    this.drawCharts();
                }, 100);

                if (result.multiple_sessions) {
                    this.showNotification(`分析完成！发现 ${result.total_sessions} 次训练`, 'success');
                } else {
                    this.showNotification(`分析完成！最佳Epoch: ${result.statistics.best_epoch}, Loss: ${result.statistics.min_loss.toFixed(6)}`, 'success');
                }
                
                // 刷新历史记录
                await this.loadAnalyzerRecords();
            }
        },

        // 更新当前统计信息
        updateCurrentStats() {
            if (!this.analyzerResult) {
                this.currentStats = {};
                return;
            }

            if (this.analyzerResult.multiple_sessions) {
                const session = this.analyzerResult.sessions[this.currentSessionIndex];
                this.currentStats = session ? session.statistics : {};
            } else {
                this.currentStats = this.analyzerResult.statistics || {};
            }
        },

        // 更新图表（切换训练会话时）
        updateCharts() {
            this.updateCurrentStats();
            this.drawCharts();
        },

        // 切换记录选择（用于对比与批量删除）
        toggleSelectRecord(recordId) {
            const index = this.selectedRecordIds.indexOf(recordId);
            if (index === -1) {
                this.selectedRecordIds.push(recordId);
            } else {
                this.selectedRecordIds.splice(index, 1);
            }
        },

        // 判断是否全部已选
        isAllSelected() {
            return this.analyzerRecords && this.analyzerRecords.length > 0 && this.selectedRecordIds.length === this.analyzerRecords.length;
        },

        // 切换全选/全不选
        toggleSelectAll() {
            if (!this.analyzerRecords || this.analyzerRecords.length === 0) return;
            if (this.isAllSelected()) {
                this.selectedRecordIds = [];
            } else {
                this.selectedRecordIds = this.analyzerRecords.map(r => r.id);
            }
        },
        
        // 当 selectedRecordIds 变化时自动加载并绘制（支持单条或多条）
        async loadAndDrawSelectedRecords() {
            if (!this.selectedRecordIds || this.selectedRecordIds.length === 0) {
                // 清除对比模式，回到单条显示当前分析结果
                this.compareMode = false;
                if (this.analyzerResult) this.drawCharts();
                return;
            }

            this.showNotification(`加载 ${this.selectedRecordIds.length} 条记录...`, 'info');
            this.compareData = [];
            for (const recordId of this.selectedRecordIds) {
                try {
                    const result = await this.apiCall(`analyzer/records/${recordId}`);
                    if (result.success && result.record) {
                        let rec = result.record;
                        // 若缺少训练底模或训练时间，尝试刷新该记录（后端重新解析日志并更新）
                        if ((!rec.pretrained_model_name_or_path || !rec.training_time) && rec.log_file_path) {
                            try {
                                const refresh = await this.apiCall(`analyzer/refresh-record/${recordId}`, 'POST');
                                if (refresh && refresh.success && refresh.record) {
                                    rec = refresh.record;
                                }
                            } catch (e) {
                                console.debug('刷新记录失败', recordId, e);
                            }
                        }
                        // 获取训练集数量（dataset_count）
                        try {
                            const trainDir = rec.train_data_dir || (rec.config && rec.config.train_data_dir) || '';
                            if (trainDir) {
                                const cntRes = await this.apiCall('analyzer/count-files', 'POST', { path: trainDir });
                                if (cntRes && cntRes.success) {
                                    rec.dataset_count = cntRes.count;
                                } else {
                                    rec.dataset_count = cntRes && cntRes.count ? cntRes.count : 'N/A';
                                }
                            } else {
                                rec.dataset_count = 'N/A';
                            }
                        } catch (e) {
                            rec.dataset_count = 'N/A';
                        }
                        this.compareData.push(rec);
                    }
                } catch (e) {
                    console.error('加载记录失败', recordId, e);
                }
            }

            if (this.compareData.length > 0) {
                this.compareMode = true;
                // 生成颜色映射
                const colors = [
                    '#2e7d32', '#1976d2', '#d32f2f', '#7b1fa2', '#f57c00',
                    '#00796b', '#5d4037', '#455a64', '#c2185b', '#512da8'
                ];
                this.selectedColors = {};
                this.compareData.forEach((rec, idx) => {
                    this.selectedColors[rec.id] = colors[idx % colors.length];
                });

                // 在当前曲线页绘制对比图
                setTimeout(() => this.drawCompareChart(), 50);
            } else {
                this.showNotification('加载对比数据失败', 'error');
            }
        },

        // 在勾选项上使用的单一入口，确保切换后立即加载并绘制
        onToggleSelect(recordId) {
            this.toggleSelectRecord(recordId);
            // 立即加载并绘制已选记录
            this.loadAndDrawSelectedRecords();
        },

        // 对比多个历史记录（使用 selectedRecordIds）
        async compareRecords() {
            if (this.selectedRecordIds.length < 2) {
                this.showNotification('请至少选择2条记录进行对比', 'warning');
                return;
            }

            this.showNotification('正在加载对比数据...', 'info');
            this.compareData = [];

            for (const recordId of this.selectedRecordIds) {
                try {
                    const result = await this.apiCall(`analyzer/records/${recordId}`);
                    if (result.success && result.record) {
                        this.compareData.push(result.record);
                    }
                } catch (error) {
                    console.error('加载记录失败:', recordId, error);
                }
            }

            if (this.compareData.length >= 2) {
                this.compareMode = true;
                this.analyzerSubTab = 'curve';
                setTimeout(() => {
                    this.drawCompareChart();
                }, 100);
                this.showNotification(`已加载 ${this.compareData.length} 条记录进行对比`, 'success');
            } else {
                this.showNotification('加载对比数据失败', 'error');
            }
        },

        // 退出对比模式
        exitCompareMode() {
            this.compareMode = false;
            this.compareData = [];
            this.selectedRecordIds = [];
            if (this.analyzerResult) {
                this.drawCharts();
            }
        },

        // 批量删除所选历史记录（会逐条调用后端删除接口）
        async bulkDeleteSelectedRecords() {
            if (!this.selectedRecordIds || this.selectedRecordIds.length === 0) return;
            if (!await this.confirmAction('确认删除', `确定要删除选中的 ${this.selectedRecordIds.length} 条记录吗？此操作无法撤销。`)) return;

            this.showNotification('正在删除所选记录...', 'info');
            const failed = [];
            for (const recordId of [...this.selectedRecordIds]) {
                try {
                    const result = await this.apiCall(`analyzer/records/${recordId}`, 'DELETE');
                    if (!result.success) {
                        failed.push(recordId);
                    }
                } catch (e) {
                    console.error('删除记录失败', recordId, e);
                    failed.push(recordId);
                }
            }

            await this.loadAnalyzerRecords();
            // 清空选择
            this.selectedRecordIds = [];

            if (failed.length === 0) {
                this.showNotification('已成功删除所选记录', 'success');
            } else {
                this.showNotification(`部分记录删除失败: ${failed.length}`, 'warning');
            }
        },

        // 绘制对比图表
        drawCompareChart() {
            // 优先使用 compareChart（在对比页），若不存在则退回到 trainingCurveChart（兼容旧逻辑）
            let canvas = document.getElementById('compareChart') || document.getElementById('trainingCurveChart');
            if (!canvas || this.compareData.length < 1) return;

            const colors = [
                '#2e7d32', '#1976d2', '#d32f2f', '#7b1fa2', '#f57c00',
                '#00796b', '#5d4037', '#455a64', '#c2185b', '#512da8'
            ];

            const datasets = this.compareData.map((record, index) => {
                // 兼容两种字段名：all_val_losses（历史记录）和 val_losses（当前分析）
                const valLosses = record.all_val_losses || record.val_losses || [];
                return {
                    label: record.model_name || `训练 ${index + 1}`,
                    data: valLosses.map(item => item.val_loss),
                    borderColor: colors[index % colors.length],
                    backgroundColor: 'transparent',
                    borderWidth: 2,
                    fill: false,
                    tension: 0.4,
                    pointRadius: 3,
                    pointStyle: 'circle',
                    cubicInterpolationMode: 'monotone'
                };
            });

            // 找到最长的epoch数
            const maxEpochs = Math.max(...this.compareData.map(r => (r.all_val_losses || r.val_losses || []).length));
            const epochs = Array.from({ length: maxEpochs }, (_, i) => i + 1);

            if (this.trainingCurveChart) {
                this.trainingCurveChart.destroy();
            }

            this.trainingCurveChart = new Chart(canvas, {
                type: 'line',
                data: { labels: epochs, datasets },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            callbacks: {
                                label: (context) => `${context.dataset.label}: ${context.raw?.toFixed(6) || 'N/A'}`
                            }
                        }
                    },
                    scales: {
                        x: { title: { display: true, text: 'Epoch' } },
                        y: { title: { display: true, text: 'Val Loss' } }
                    }
                }
            });
        },

        // 绘制图表
        drawCharts() {
            this.drawTrainingCurve();
            this.drawTop10Chart();
        },

        // 绘制训练曲线
        drawTrainingCurve() {
            const canvas = document.getElementById('trainingCurveChart');
            if (!canvas) return;

            // 获取当前数据
            let valLosses = [];
            if (this.analyzerResult.multiple_sessions) {
                const session = this.analyzerResult.sessions[this.currentSessionIndex];
                valLosses = session ? session.val_losses : [];
            } else {
                valLosses = this.analyzerResult.val_losses || [];
            }

            if (valLosses.length === 0) return;

            const epochs = valLosses.map(item => item.epoch);
            const losses = valLosses.map(item => item.val_loss);
            
            // 找到最低Loss的索引
            const minLoss = Math.min(...losses);
            const minLossIndex = losses.indexOf(minLoss);
            
            // 为每个点设置颜色，最低点用红色标记（大小一致，悬停时放大）
            const pointColors = losses.map((_, idx) => idx === minLossIndex ? '#ff0000' : '#2e7d32');
            const pointBorderColors = losses.map((_, idx) => idx === minLossIndex ? '#ff0000' : '#2e7d32');
            const pointHoverRadii = losses.map((_, idx) => idx === minLossIndex ? 12 : 8);

            // 销毁旧图表
            if (this.trainingCurveChart) {
                this.trainingCurveChart.destroy();
            }

            // 保存valLosses引用供tooltip使用
            const valLossesData = valLosses;

            // 创建新图表
            this.trainingCurveChart = new Chart(canvas, {
                type: 'line',
                data: {
                    labels: epochs,
                    datasets: [{
                        label: 'Val Loss',
                        data: losses,
                        borderColor: '#2e7d32',
                        backgroundColor: 'rgba(46, 125, 50, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4,
                        pointRadius: 4,
                        pointBackgroundColor: pointColors,
                        pointBorderColor: pointBorderColors,
                        pointBorderWidth: 2,
                        pointHoverRadius: pointHoverRadii,
                        pointHoverBackgroundColor: pointColors,
                        pointHoverBorderColor: '#fff',
                        pointHoverBorderWidth: 2,
                        cubicInterpolationMode: 'monotone'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {
                        mode: 'index',
                        intersect: false
                    },
                    plugins: {
                        legend: { display: true },
                        tooltip: {
                            enabled: true,
                            backgroundColor: 'rgba(0, 0, 0, 0.85)',
                            titleColor: '#fff',
                            bodyColor: '#fff',
                            borderColor: '#2e7d32',
                            borderWidth: 1,
                            cornerRadius: 8,
                            padding: 12,
                            displayColors: false,
                            titleFont: { size: 14, weight: 'bold' },
                            bodyFont: { size: 13 },
                            callbacks: {
                                title: (context) => {
                                    const idx = context[0].dataIndex;
                                    const epoch = epochs[idx];
                                    const isMin = idx === minLossIndex;
                                    return isMin ? `🏆 Epoch ${epoch} (最佳)` : `Epoch ${epoch}`;
                                },
                                label: (context) => {
                                    const idx = context.dataIndex;
                                    const loss = losses[idx];
                                    const item = valLossesData[idx];
                                    const lines = [`Val Loss: ${loss.toFixed(6)}`];
                                    
                                    // 如果有步数范围信息，显示它
                                    if (item && item.step_range) {
                                        lines.push(`步数范围: ${item.step_range}`);
                                    }
                                    if (item && item.step_count) {
                                        lines.push(`采样步数: ${item.step_count}`);
                                    }
                                    
                                    return lines;
                                },
                                afterLabel: (context) => {
                                    const idx = context.dataIndex;
                                    if (idx === minLossIndex) {
                                        return '✓ 推荐使用此Epoch的模型';
                                    }
                                    return '';
                                }
                            }
                        }
                    },
                    scales: {
                        x: { 
                            title: { display: true, text: 'Epoch' },
                            grid: { color: 'rgba(0, 0, 0, 0.05)' }
                        },
                        y: { 
                            title: { display: true, text: 'Val Loss' },
                            grid: { color: 'rgba(0, 0, 0, 0.05)' }
                        }
                    },
                    onHover: (event, elements) => {
                        canvas.style.cursor = elements.length > 0 ? 'pointer' : 'default';
                    }
                }
            });
        },

        // 绘制 Top10 柱状图
        drawTop10Chart() {
            const canvas = document.getElementById('top10Chart');
            if (!canvas || !this.currentStats.top_10) return;

            const top10 = this.currentStats.top_10;
            const labels = top10.map(item => `Epoch ${item.epoch}`);
            const data = top10.map(item => item.val_loss);

            // 生成渐变颜色（从深绿到浅绿）
            const colors = top10.map((_, idx) => {
                const ratio = idx / (top10.length - 1 || 1);
                const r = Math.round(46 + (165 - 46) * ratio);
                const g = Math.round(125 + (214 - 125) * ratio);
                const b = Math.round(50 + (167 - 50) * ratio);
                return `rgb(${r}, ${g}, ${b})`;
            });

            // 销毁旧图表
            if (this.top10Chart) {
                this.top10Chart.destroy();
            }

            // 保存top10数据供tooltip使用
            const top10Data = top10;

            // 创建新图表
            this.top10Chart = new Chart(canvas, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Val Loss',
                        data: data,
                        backgroundColor: colors,
                        borderColor: colors.map(c => c.replace('rgb', 'rgba').replace(')', ', 1)')),
                        borderWidth: 1,
                        borderRadius: 4,
                        hoverBackgroundColor: colors.map(c => c.replace('rgb', 'rgba').replace(')', ', 0.8)')),
                        hoverBorderColor: '#2e7d32',
                        hoverBorderWidth: 2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            enabled: true,
                            backgroundColor: 'rgba(0, 0, 0, 0.85)',
                            titleColor: '#fff',
                            bodyColor: '#fff',
                            borderColor: '#2e7d32',
                            borderWidth: 1,
                            cornerRadius: 8,
                            padding: 12,
                            displayColors: false,
                            titleFont: { size: 14, weight: 'bold' },
                            bodyFont: { size: 13 },
                            callbacks: {
                                title: (context) => {
                                    const idx = context[0].dataIndex;
                                    const item = top10Data[idx];
                                    const rank = idx + 1;
                                    return rank === 1 ? `🥇 第${rank}名 - Epoch ${item.epoch}` : 
                                           rank === 2 ? `🥈 第${rank}名 - Epoch ${item.epoch}` :
                                           rank === 3 ? `🥉 第${rank}名 - Epoch ${item.epoch}` :
                                           `第${rank}名 - Epoch ${item.epoch}`;
                                },
                                label: (context) => {
                                    const loss = context.raw;
                                    return `Val Loss: ${loss.toFixed(6)}`;
                                },
                                afterLabel: (context) => {
                                    const idx = context.dataIndex;
                                    if (idx === 0) {
                                        return '✓ 最佳模型';
                                    }
                                    return '';
                                }
                            }
                        }
                    },
                    scales: {
                        y: { 
                            title: { display: true, text: 'Val Loss' },
                            grid: { color: 'rgba(0, 0, 0, 0.05)' }
                        },
                        x: {
                            grid: { display: false }
                        }
                    },
                    onHover: (event, elements) => {
                        canvas.style.cursor = elements.length > 0 ? 'pointer' : 'default';
                    }
                }
            });
        },

        // 打开 Markdown 弹窗并生成内容
        openMarkdownModal() {
            this.markdownContent = this.generateTrainingMarkdown();
            this.showMarkdownModal = true;
        },

        // 生成训练表格的 Markdown 内容（整合当前分析与历史记录）
        generateTrainingMarkdown() {
            // 表头固定
            const header = '| 横轴分类 - 模型名称|训练集数量|epoch|repeat|save epoch|rank|steps|训练底模|学习率|训练时间|\\n|---|---|---|---|---|---|---|---|---|---|\\n';

            let rows = '';

            // 优先使用当前 analyzerResult 的训练会话或单次结果
            const pushConfig = (config, statistics) => {
                if (!config) return;
                const modelName = config.model_name || config.save_name || (config.output_dir ? config.output_dir.split(/[/\\\\]/).pop() : 'N/A');
                const trainData = (config.train_data_dir || 'N/A').split(/[/\\\\]/).pop() || 'N/A';
                const epoch = config.num_train_epochs || config.num_epochs || (statistics && statistics.total_epochs) || 'N/A';
                const repeat = config.repeats != null ? config.repeats : (config.repeat != null ? config.repeat : 'N/A');
                const saveEpoch = config.save_model_epochs != null ? config.save_model_epochs : (config.save_epoch != null ? config.save_epoch : 'N/A');
                const rank = config.rank != null ? config.rank : (config.world_size != null ? config.world_size : 'N/A');
                const steps = config.steps != null ? config.steps : 'N/A';
                const baseModel = (() => {
                    const path = config.pretrained_model_name_or_path || config.pretrained_model || '';
                    return path ? path.split(/[/\\\\]/).pop() : 'N/A';
                })();
                const lr = config.learning_rate != null ? config.learning_rate : config.lr != null ? config.lr : 'N/A';
                const time = config.training_time || 'N/A';

                rows += `| ${modelName} | ${trainData} | ${epoch} | ${repeat} | ${saveEpoch} | ${rank} | ${steps} | ${baseModel} | ${lr} | ${time} |\\n`;
            };

            if (this.analyzerResult) {
                if (this.analyzerResult.training_sessions && this.analyzerResult.training_sessions.length > 0) {
                    this.analyzerResult.training_sessions.forEach(s => {
                        pushConfig(s.config || {}, s.statistics || {});
                    });
                } else {
                    pushConfig(this.analyzerResult.config || {}, this.analyzerResult.statistics || {});
                }
            }

            // 合并历史记录（analyzerRecords）
            if (this.analyzerRecords && this.analyzerRecords.length > 0) {
                this.analyzerRecords.forEach(rec => {
                    // rec 应包含 config 字段或 summary 字段，以兼容现有结构
                    const config = rec.config || {
                        model_name: rec.model_name,
                        num_train_epochs: rec.num_epochs,
                        learning_rate: rec.learning_rate,
                        save_model_epochs: rec.save_model_epochs,
                        rank: rec.rank,
                        train_data_dir: rec.train_data_dir,
                        pretrained_model_name_or_path: rec.pretrained_model
                    };
                    pushConfig(config, rec.statistics || {});
                });
            }

            return header + rows;
        },

        // 将 markdown 发送到后端写入文件
        async saveMarkdownToServer() {
            try {
                const content = this.markdownContent || this.generateTrainingMarkdown();
                const res = await this.apiCall('analyzer/export-markdown', 'POST', { content });
                if (res && res.success) {
                    this.showNotification('训练表格已保存到 training_excel.md', 'success');
                } else {
                    this.showNotification('保存失败: ' + (res.message || '未知错误'), 'error');
                }
            } catch (e) {
                this.showNotification('保存失败: ' + e.message, 'error');
            }
        },

        // 加载历史记录
        async loadAnalyzerRecords() {
            const result = await this.apiCall('analyzer/records');
            if (result.success) {
                this.analyzerRecords = result.records || [];
            }
        },

        // 查看记录详情
        async viewRecord(recordId) {
            const result = await this.apiCall(`analyzer/records/${recordId}`);
            if (result.success) {
                this.recordDetail = result.record;
                this.showRecordDetail = true;
            }
        },

        // 删除分析记录
        async deleteAnalyzerRecord(recordId) {
            if (!await this.confirmAction('确认删除', '确定要删除这条记录吗？')) return;
            
            const result = await this.apiCall(`analyzer/records/${recordId}`, 'DELETE');
            if (result.success) {
                this.showNotification('记录已删除', 'success');
                await this.loadAnalyzerRecords();
            }
        },

        // ==================== Chat 对话方法 ====================
        
        // 初始化 Chat（从后端加载历史会话）
        async initChat() {
            await this.loadChatSessionsFromServer();
            
            // 如果没有会话，创建一个新的
            if (this.chatSessions.length === 0) {
                this.createNewChat();
            } else {
                // 加载最后一个会话
                await this.loadChatSession(this.chatSessions[0].id);
            }
        },
        
        // 从服务器加载会话列表
        async loadChatSessionsFromServer() {
            const result = await this.apiCall('chat/sessions');
            if (result.success) {
                this.chatSessions = result.sessions || [];
            }
        },
        
        // 保存当前会话到服务器
        async saveChatSessionToServer() {
            const session = this.chatSessions.find(s => s.id === this.currentChatSessionId);
            if (session) {
                await this.apiCall('chat/session', 'POST', {
                    id: session.id,
                    title: session.title,
                    messages: this.chatMessages,
                    created_at: session.created_at
                });
            }
        },
        
        // 创建新对话
        createNewChat() {
            const newSession = {
                id: Date.now().toString(),
                title: '新对话',
                created_at: new Date().toLocaleString('zh-CN'),
                updated_at: new Date().toLocaleString('zh-CN'),
                messages: [],
                message_count: 0
            };
            
            this.chatSessions.unshift(newSession);
            this.currentChatSessionId = newSession.id;
            this.chatMessages = [];
        },
        
        // 加载对话会话
        async loadChatSession(sessionId) {
            // 从服务器加载完整会话内容
            const result = await this.apiCall(`chat/session/${sessionId}`);
            if (result.success && result.session) {
                this.currentChatSessionId = sessionId;
                this.chatMessages = result.session.messages || [];
                
                // 滚动到底部
                this.$nextTick(() => {
                    const chatContainer = this.$refs.chatMessages;
                    if (chatContainer) {
                        chatContainer.scrollTop = chatContainer.scrollHeight;
                    }
                });
            } else {
                // 如果加载失败，使用本地数据
                const session = this.chatSessions.find(s => s.id === sessionId);
                if (session) {
                    this.currentChatSessionId = sessionId;
                    this.chatMessages = session.messages || [];
                }
            }
        },
        
        // 删除对话会话
        async deleteChatSession(sessionId) {
            const result = await this.apiCall(`chat/session/${sessionId}`, 'DELETE');
            if (result.success) {
                const index = this.chatSessions.findIndex(s => s.id === sessionId);
                if (index !== -1) {
                    this.chatSessions.splice(index, 1);
                }
                
                // 如果删除的是当前会话，切换到其他会话或创建新会话
                if (this.currentChatSessionId === sessionId) {
                    if (this.chatSessions.length > 0) {
                        await this.loadChatSession(this.chatSessions[0].id);
                    } else {
                        this.createNewChat();
                    }
                }
                
                this.showNotification('对话已删除', 'success');
            }
        },
        
        // 更新当前会话（保存到服务器）
        async updateCurrentSession() {
            const session = this.chatSessions.find(s => s.id === this.currentChatSessionId);
            if (session) {
                session.messages = [...this.chatMessages];
                session.message_count = this.chatMessages.length;
                session.updated_at = new Date().toLocaleString('zh-CN');
                
                // 更新标题（使用第一条用户消息）
                if (this.chatMessages.length > 0 && session.title === '新对话') {
                    const firstUserMsg = this.chatMessages.find(m => m.role === 'user');
                    if (firstUserMsg) {
                        session.title = firstUserMsg.content.substring(0, 20) + (firstUserMsg.content.length > 20 ? '...' : '');
                    }
                }
                
                // 保存到服务器
                await this.saveChatSessionToServer();
            }
        },
        
        // 获取当前对话标题
        getCurrentChatTitle() {
            const session = this.chatSessions.find(s => s.id === this.currentChatSessionId);
            return session ? session.title : 'AI 对话助手';
        },
        
        // 获取 Chat 可用模型列表
        getChatModels() {
            const currentProvider = this.apikeyConfig.providers[this.apikeyConfig.current_provider];
            if (currentProvider && currentProvider.models) {
                return currentProvider.models;
            }
            return [];
        },
        
        // 处理 Enter 键
        handleChatEnter(event) {
            if (!event.shiftKey) {
                event.preventDefault();
                this.sendChatMessage();
            }
        },
        
        // 发送聊天消息
        async sendChatMessage() {
            const message = this.chatInput.trim();
            if (!message || this.isChatLoading) return;
            
            // 添加用户消息
            this.chatMessages.push({
                role: 'user',
                content: message,
                time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
            });
            
            this.chatInput = '';
            this.isChatLoading = true;
            
            // 滚动到底部
            this.$nextTick(() => {
                const chatContainer = this.$refs.chatMessages;
                if (chatContainer) {
                    chatContainer.scrollTop = chatContainer.scrollHeight;
                }
            });
            
            try {
                // 获取当前配置
                const currentProvider = this.apikeyConfig.providers[this.apikeyConfig.current_provider];
                const apiKey = currentProvider ? currentProvider.api_key : '';
                
                if (!apiKey) {
                    this.showNotification('请先在配置中心设置 API Key', 'error');
                    this.chatMessages.pop();
                    return;
                }
                
                // 调用后端 API
                const result = await this.apiCall('chat/message', 'POST', {
                    message: message,
                    model: this.chatModel,
                    history: this.chatMessages.slice(0, -1).map(msg => ({
                        role: msg.role,
                        content: msg.content
                    }))
                });
                
                if (result.success) {
                    // 添加 AI 回复
                    this.chatMessages.push({
                        role: 'assistant',
                        content: result.reply,
                        time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
                    });
                    
                    // 更新当前会话
                    this.updateCurrentSession();
                } else {
                    this.showNotification(result.message || '发送失败', 'error');
                    this.chatMessages.pop();
                }
            } catch (error) {
                console.error('Chat error:', error);
                this.showNotification('发送失败: ' + error.message, 'error');
                this.chatMessages.pop();
            } finally {
                this.isChatLoading = false;
                
                // 滚动到底部
                this.$nextTick(() => {
                    const chatContainer = this.$refs.chatMessages;
                    if (chatContainer) {
                        chatContainer.scrollTop = chatContainer.scrollHeight;
                    }
                });
            }
        },
        
        // 清空当前对话
        clearCurrentChat() {
            this.chatMessages = [];
            this.updateCurrentSession();
            this.showNotification('对话已清空', 'success');
        },

        // ==================== 详情弹窗翻译功能 ====================
        
        // 将原文按句号分割成句子数组
        splitOriginalToSentences(text) {
            if (!text) return [];
            // 按句号分割（英文句号），保留句号
            return text.split(/(?<=\.)\s*/)
                .map(s => s.trim())
                .filter(s => s.length > 0);
        },
        
        // 将翻译文本按 / 分割成句子数组
        splitTranslatedToSentences(text) {
            if (!text) return [];
            // 按 / 分割
            return text.split('/')
                .map(s => s.trim())
                .filter(s => s.length > 0);
        },
        
        // 切换句子对照模式
        toggleSentenceMapping() {
            this.showSentenceMapping = !this.showSentenceMapping;
            if (this.showSentenceMapping) {
                this.updateSentenceMapping();
            }
        },
        
        // 更新句子映射
        updateSentenceMapping() {
            const originalText = this.detailImage?.text || this.detailPair?.text || '';
            const translatedText = this.detailImage?.translatedText || this.detailPair?.translatedText || '';
            
            this.originalSentences = this.splitOriginalToSentences(originalText);
            this.translatedSentences = this.splitTranslatedToSentences(translatedText);
            // 保存原始翻译句子（用于后续比较修改）
            this.initialTranslatedSentences = [...this.translatedSentences];
            // 初始化修改标记数组（全部为 false，表示未修改）
            this.modifiedSentenceFlags = new Array(this.translatedSentences.length).fill(false);
            
            // 同步初始化 sentenceDataStore
            this.sentenceDataStore = this.translatedSentences.map((sentence, index) => ({
                index: index,
                originalContent: sentence,
                currentContent: sentence,
                dirty: false
            }));
        },
        
        // 生成带标记的原文HTML
        getMarkedOriginalHtml() {
            if (!this.originalSentences || this.originalSentences.length === 0) {
                return this.detailImage?.text || '';
            }
            
            const colors = ['#3B82F6', '#10B981', '#F59E0B', '#EC4899', '#8B5CF6', '#6366F1', '#EF4444', '#F97316'];
            let html = '';
            
            this.originalSentences.forEach((sentence, index) => {
                const color = colors[index % colors.length];
                const escapedSentence = sentence.replace(/</g, '&lt;').replace(/>/g, '&gt;');
                html += `<span data-sentence-index="${index}">${escapedSentence}</span>`;
                html += `<span class="sentence-marker" contenteditable="false" style="display:inline-flex;align-items:center;justify-content:center;width:16px;height:16px;font-size:10px;font-weight:bold;color:white;background-color:${color};border-radius:50%;margin-left:4px;vertical-align:middle;user-select:none;">${index + 1}</span>`;
                if (index < this.originalSentences.length - 1) {
                    html += ' ';
                }
            });
            
            return html;
        },
        
        // 从带标记的视图更新原文文本
        updateOriginalTextFromMarkedView(event) {
            const el = event.target;
            // 提取纯文本（移除标记）
            const text = this.extractTextFromMarkedView(el);
            if (this.detailImage) {
                this.detailImage.text = text;
            } else if (this.detailPair) {
                this.detailPair.text = text;
            }
        },
        
        // 从带标记的元素中提取纯文本
        extractTextFromMarkedView(el) {
            let text = '';
            el.childNodes.forEach(node => {
                if (node.nodeType === Node.TEXT_NODE) {
                    text += node.textContent;
                } else if (node.nodeType === Node.ELEMENT_NODE) {
                    if (!node.classList.contains('sentence-marker')) {
                        text += node.textContent;
                    }
                }
            });
            return text.trim();
        },
        
        // 带标记视图输入时的处理
        onMarkedViewInput(event) {
            const el = event.target;
            const text = this.extractTextFromMarkedView(el);
            if (this.detailImage) {
                this.detailImage.text = text;
            } else if (this.detailPair) {
                this.detailPair.text = text;
            }
        },
        
        // 初始化句子数据存储（在翻译完成或切换到句子模式时调用）
        initSentenceDataStore() {
            const translatedText = this.detailImage?.translatedText || this.detailPair?.translatedText || '';
            const sentences = this.splitTranslatedToSentences(translatedText);
            
            this.sentenceDataStore = sentences.map((sentence, index) => ({
                index: index,
                originalContent: sentence,
                currentContent: sentence,
                dirty: false
            }));
            
            // 同步到 translatedSentences 数组
            this.translatedSentences = sentences;
            this.initialTranslatedSentences = [...sentences];
            this.modifiedSentenceFlags = new Array(sentences.length).fill(false);
        },
        
        // 生成带标记的翻译HTML（支持句级编辑追踪）
        getMarkedTranslatedHtml() {
            // 如果数据存储为空，先初始化
            if (!this.sentenceDataStore || this.sentenceDataStore.length === 0) {
                const translatedText = this.detailImage?.translatedText || this.detailPair?.translatedText || '';
                if (!translatedText) return '';
                this.initSentenceDataStore();
            }
            
            if (this.sentenceDataStore.length === 0) {
                return this.detailImage?.translatedText || this.detailPair?.translatedText || '';
            }
            
            const colors = ['#3B82F6', '#10B981', '#F59E0B', '#EC4899', '#8B5CF6', '#6366F1', '#EF4444', '#F97316'];
            let html = '';
            
            this.sentenceDataStore.forEach((sentenceData, index) => {
                const color = colors[index % colors.length];
                const escapedSentence = sentenceData.currentContent.replace(/</g, '&lt;').replace(/>/g, '&gt;');
                // 如果句子被修改，添加 modified 类和样式
                const modifiedClass = sentenceData.dirty ? 'modified' : '';
                const modifiedStyle = sentenceData.dirty ? 'background-color: #FEF3C7; font-weight: 500;' : '';
                
                html += `<span class="sentence ${modifiedClass}" data-sentence-index="${index}" style="${modifiedStyle}">${escapedSentence}</span>`;
                html += `<span class="sentence-marker" contenteditable="false" style="display:inline-flex;align-items:center;justify-content:center;width:16px;height:16px;font-size:10px;font-weight:bold;color:white;background-color:${color};border-radius:50%;margin-left:4px;vertical-align:middle;user-select:none;">${index + 1}</span>`;
                if (index < this.sentenceDataStore.length - 1) {
                    html += ' ';
                }
            });
            
            return html;
        },
        
        // 渲染带标记的翻译HTML到DOM（只在需要时调用，不会自动触发）
        renderMarkedTranslatedHtml() {
            const el = this.$refs.markedTranslatedText;
            if (!el) return;
            
            // 初始化数据存储
            this.initSentenceDataStore();
            
            // 生成HTML并渲染
            const html = this.getMarkedTranslatedHtml();
            el.innerHTML = html;
        },
        
        // 渲染带标记的翻译HTML到DOM（图像编辑模式专用）
        renderMarkedTranslatedHtmlForPair() {
            const el = this.$refs.markedTranslatedTextPair;
            if (!el) return;
            
            // 初始化数据存储
            this.initSentenceDataStore();
            
            // 生成HTML并渲染
            const html = this.getMarkedTranslatedHtml();
            el.innerHTML = html;
        },
        
        // 渲染带标记的原文HTML到DOM（图像编辑模式专用）
        renderMarkedOriginalHtmlForPair() {
            const el = this.$refs.markedOriginalTextPair;
            if (!el) return;
            
            // 生成HTML并渲染
            const html = this.getMarkedOriginalHtml();
            el.innerHTML = html;
        },
        
        // 处理键盘事件（确保方向键正常工作）
        onTranslatedTextKeydown(event) {
            // 允许所有键盘操作正常进行，不阻止默认行为
            // 方向键、Home、End、Delete、Backspace 等都应该正常工作
        },
        
        // 处理输入法组合开始（中文输入法）
        onCompositionStart(event) {
            this.isComposing = true;
        },
        
        // 处理输入法组合结束（中文输入法）
        onCompositionEnd(event) {
            this.isComposing = false;
            // 组合结束后，手动触发一次输入处理
            this.handleSentenceInput(event);
        },
        
        // 处理句子编辑输入（不重新渲染DOM，只更新数据）
        handleSentenceInput(event) {
            // 如果正在输入法组合中，不处理
            if (this.isComposing) return;
            
            const el = event.target;
            if (!el) return;
            
            // 获取当前光标所在的 span 元素
            const selection = window.getSelection();
            if (!selection || selection.rangeCount === 0) return;
            
            const range = selection.getRangeAt(0);
            let currentNode = range.startContainer;
            
            // 向上查找最近的 sentence span
            let sentenceSpan = null;
            while (currentNode && currentNode !== el) {
                if (currentNode.nodeType === Node.ELEMENT_NODE && 
                    currentNode.classList && 
                    currentNode.classList.contains('sentence')) {
                    sentenceSpan = currentNode;
                    break;
                }
                currentNode = currentNode.parentNode;
            }
            
            if (!sentenceSpan) {
                // 如果没找到，尝试从容器中提取所有句子内容并更新
                this.updateAllSentencesFromDOM(el);
                return;
            }
            
            const index = parseInt(sentenceSpan.getAttribute('data-sentence-index'), 10);
            if (isNaN(index) || index < 0 || index >= this.sentenceDataStore.length) return;
            
            // 获取当前 span 的文本内容
            const newContent = sentenceSpan.textContent || '';
            const sentenceData = this.sentenceDataStore[index];
            
            // 更新数据存储
            sentenceData.currentContent = newContent;
            
            // 检查是否与原始内容不同，标记为 dirty
            const isDirty = sentenceData.currentContent.trim() !== sentenceData.originalContent.trim();
            
            if (isDirty !== sentenceData.dirty) {
                sentenceData.dirty = isDirty;
                // 只更新样式，不重新渲染整个DOM
                if (isDirty) {
                    sentenceSpan.classList.add('modified');
                    sentenceSpan.style.backgroundColor = '#FEF3C7';
                    sentenceSpan.style.fontWeight = '500';
                } else {
                    sentenceSpan.classList.remove('modified');
                    sentenceSpan.style.backgroundColor = '';
                    sentenceSpan.style.fontWeight = '';
                }
            }
            
            // 同步更新 translatedSentences 和 modifiedSentenceFlags
            this.translatedSentences[index] = newContent;
            this.modifiedSentenceFlags[index] = isDirty;
            
            // 同步更新翻译文本（不触发DOM重新渲染）
            this.syncTranslatedTextFromDataStore();
        },
        
        // 从DOM中更新所有句子内容（处理跨句编辑的情况）
        updateAllSentencesFromDOM(containerEl) {
            const sentenceSpans = containerEl.querySelectorAll('.sentence');
            
            // 创建一个 Set 记录 DOM 中存在的句子索引
            const existingIndices = new Set();
            
            sentenceSpans.forEach((span) => {
                const index = parseInt(span.getAttribute('data-sentence-index'), 10);
                if (isNaN(index) || index < 0 || index >= this.sentenceDataStore.length) return;
                
                existingIndices.add(index);
                
                const newContent = span.textContent || '';
                const sentenceData = this.sentenceDataStore[index];
                
                sentenceData.currentContent = newContent;
                const isDirty = sentenceData.currentContent.trim() !== sentenceData.originalContent.trim();
                
                if (isDirty !== sentenceData.dirty) {
                    sentenceData.dirty = isDirty;
                    if (isDirty) {
                        span.classList.add('modified');
                        span.style.backgroundColor = '#FEF3C7';
                        span.style.fontWeight = '500';
                    } else {
                        span.classList.remove('modified');
                        span.style.backgroundColor = '';
                        span.style.fontWeight = '';
                    }
                }
                
                this.translatedSentences[index] = newContent;
                this.modifiedSentenceFlags[index] = isDirty;
            });
            
            // 检测被删除的句子（DOM 中不存在但 sentenceDataStore 中存在的）
            this.sentenceDataStore.forEach((sentenceData, index) => {
                if (!existingIndices.has(index)) {
                    // 该句子的 span 已被删除，标记为空内容且 dirty
                    sentenceData.currentContent = '';
                    sentenceData.dirty = true;
                    this.translatedSentences[index] = '';
                    this.modifiedSentenceFlags[index] = true;
                    console.log(`[updateAllSentencesFromDOM] 检测到句子 ${index} 被删除`);
                }
            });
            
            // 检测新增的文本（在句子标记之外的文本）
            this.detectNewAddedText(containerEl);
            
            this.syncTranslatedTextFromDataStore();
        },
        
        // 检测新增的文本（在句子标记之外添加的文本）
        detectNewAddedText(containerEl) {
            // 获取容器中所有的文本节点（不在 .sentence 或 .sentence-marker 内的）
            const walker = document.createTreeWalker(
                containerEl,
                NodeFilter.SHOW_TEXT,
                {
                    acceptNode: function(node) {
                        // 检查父节点是否是 sentence 或 sentence-marker
                        let parent = node.parentNode;
                        while (parent && parent !== containerEl) {
                            if (parent.classList && 
                                (parent.classList.contains('sentence') || parent.classList.contains('sentence-marker'))) {
                                return NodeFilter.FILTER_REJECT;
                            }
                            parent = parent.parentNode;
                        }
                        return NodeFilter.FILTER_ACCEPT;
                    }
                }
            );
            
            let newTexts = [];
            let node;
            while (node = walker.nextNode()) {
                const text = node.textContent.trim();
                if (text && text.length > 0) {
                    // 过滤掉只有空格或标点的文本
                    const cleanText = text.replace(/^[\s\/\,\.\。\，]+|[\s\/\,\.\。\，]+$/g, '').trim();
                    if (cleanText.length > 0) {
                        newTexts.push(cleanText);
                    }
                }
            }
            
            // 如果检测到新增文本，添加到 pendingNewSentences
            if (newTexts.length > 0) {
                this.pendingNewSentences = newTexts;
                console.log('[detectNewAddedText] 检测到新增文本:', newTexts);
            } else {
                this.pendingNewSentences = [];
            }
        },
        
        // 从数据存储同步翻译文本（不触发DOM重新渲染）
        syncTranslatedTextFromDataStore() {
            const newText = this.sentenceDataStore.map(s => s.currentContent).join(' / ');
            if (this.detailImage) {
                this.detailImage.translatedText = newText;
            } else if (this.detailPair) {
                this.detailPair.translatedText = newText;
            }
        },
        
        // 从带标记的翻译视图更新翻译文本（blur时调用）
        updateTranslatedTextFromMarkedView(event) {
            const el = event.target;
            // 更新所有句子数据
            this.updateAllSentencesFromDOM(el);
        },
        
        // 带标记翻译视图输入时的处理
        onMarkedTranslatedViewInput(event) {
            // 如果正在输入法组合中，不处理
            if (this.isComposing) return;
            this.handleSentenceInput(event);
        },
        
        // 获取增量同步的 JSON Payload
        getIncrementalSyncPayload() {
            const updates = [];
            
            this.sentenceDataStore.forEach((sentenceData, index) => {
                if (sentenceData.dirty) {
                    updates.push({
                        index: index,
                        new_content: sentenceData.currentContent
                    });
                }
            });
            
            return {
                full_text: this.detailImage?.translatedText || this.detailPair?.translatedText || '',
                updates: updates
            };
        },
        
        // 重置句子数据存储（清除所有修改标记）
        resetSentenceDataStore() {
            this.sentenceDataStore.forEach(sentenceData => {
                sentenceData.currentContent = sentenceData.originalContent;
                sentenceData.dirty = false;
            });
            this.translatedSentences = this.sentenceDataStore.map(s => s.originalContent);
            this.modifiedSentenceFlags = new Array(this.sentenceDataStore.length).fill(false);
            this.syncTranslatedTextFromDataStore();
        },
        
        // 确认同步后更新原始内容（将当前内容设为新的原始内容）
        commitSentenceChanges() {
            this.sentenceDataStore.forEach(sentenceData => {
                sentenceData.originalContent = sentenceData.currentContent;
                sentenceData.dirty = false;
            });
            this.initialTranslatedSentences = [...this.translatedSentences];
            this.modifiedSentenceFlags = new Array(this.sentenceDataStore.length).fill(false);
        },
        
        // 智能同步标签：只同步被修改的句子（蓝色标记的句子）
        async smartSyncTranslation() {
            console.log('[smartSyncTranslation] 开始执行');
            console.log('[smartSyncTranslation] modifiedSentenceFlags:', this.modifiedSentenceFlags);
            
            if (!this.detailImage?.translatedText && !this.detailPair?.translatedText) {
                // 检查是否有被删除的句子需要同步
                const hasDeletedSentences = this.sentenceDataStore && this.sentenceDataStore.some(s => s.dirty && !s.currentContent.trim());
                if (!hasDeletedSentences) {
                    this.showNotification('没有可同步的翻译文本', 'warning');
                    return;
                }
            }
            
            // 确保句子映射已更新
            if (this.originalSentences.length === 0 && (!this.sentenceDataStore || this.sentenceDataStore.length === 0)) {
                this.updateSentenceMapping();
            }
            
            // 使用 sentenceDataStore 获取修改的句子（优先）或回退到 modifiedSentenceFlags
            const modifiedIndices = [];
            const deletedIndices = [];  // 记录被删除的句子索引
            
            if (this.sentenceDataStore && this.sentenceDataStore.length > 0) {
                this.sentenceDataStore.forEach((sentenceData, index) => {
                    if (sentenceData.dirty) {
                        // 检查是否是删除操作（内容为空）
                        if (!sentenceData.currentContent.trim()) {
                            deletedIndices.push(index);
                        } else {
                            modifiedIndices.push(index);
                        }
                    }
                });
            } else {
                for (let i = 0; i < this.modifiedSentenceFlags.length; i++) {
                    if (this.modifiedSentenceFlags[i] === true) {
                        // 检查是否是删除操作
                        if (!this.translatedSentences[i] || !this.translatedSentences[i].trim()) {
                            deletedIndices.push(i);
                        } else {
                            modifiedIndices.push(i);
                        }
                    }
                }
            }
            
            console.log('[smartSyncTranslation] modifiedIndices:', modifiedIndices);
            console.log('[smartSyncTranslation] deletedIndices:', deletedIndices);
            console.log('[smartSyncTranslation] pendingNewSentences:', this.pendingNewSentences);
            
            // 检查是否有新增的句子
            const hasNewSentences = this.pendingNewSentences && this.pendingNewSentences.length > 0;
            
            if (modifiedIndices.length === 0 && deletedIndices.length === 0 && !hasNewSentences) {
                this.showNotification('没有检测到修改的句子', 'info');
                return;
            }
            
            this.isSyncingTranslation = true;
            try {
                const targetLang = this.detailTranslateLang === 'zh' ? 'en' : 'zh';
                let syncCount = 0;
                let deleteCount = 0;
                let addCount = 0;
                
                // 处理修改的句子（需要翻译回原语言）
                for (const index of modifiedIndices) {
                    const translatedText = this.translatedSentences[index];
                    if (!translatedText || !translatedText.trim()) continue;
                    
                    // 将修改后的翻译句子翻译回原语言
                    const result = await this.apiCall('translate', 'POST', {
                        text: translatedText,
                        target_lang: targetLang,
                        model_id: this.translateModelId,
                        provider: this.translateProvider
                    });
                    
                    if (result.success) {
                        // 去除翻译结果中的 / 分隔符（同步时不需要）
                        let cleanedText = result.translated.replace(/\s*\/\s*/g, ' ').trim();
                        cleanedText = cleanedText.replace(/\/+$/, '').trim();
                        
                        // 更新对应的原文句子
                        if (index < this.originalSentences.length) {
                            this.originalSentences[index] = cleanedText;
                        } else {
                            // 如果是新增的句子，添加到原文数组
                            this.originalSentences.push(cleanedText);
                        }
                        
                        // 同步成功后，更新初始值并清除修改标记
                        this.initialTranslatedSentences[index] = translatedText;
                        this.modifiedSentenceFlags.splice(index, 1, false);
                        
                        // 同步更新 sentenceDataStore
                        if (this.sentenceDataStore && this.sentenceDataStore[index]) {
                            this.sentenceDataStore[index].originalContent = this.sentenceDataStore[index].currentContent;
                            this.sentenceDataStore[index].dirty = false;
                        }
                        
                        syncCount++;
                    }
                }
                
                // 处理删除的句子（从后往前删除，避免索引错乱）
                if (deletedIndices.length > 0) {
                    // 按索引从大到小排序
                    deletedIndices.sort((a, b) => b - a);
                    
                    for (const index of deletedIndices) {
                        // 删除原文句子
                        if (index < this.originalSentences.length) {
                            this.originalSentences.splice(index, 1);
                        }
                        // 删除翻译句子
                        if (index < this.translatedSentences.length) {
                            this.translatedSentences.splice(index, 1);
                        }
                        // 删除初始翻译句子
                        if (index < this.initialTranslatedSentences.length) {
                            this.initialTranslatedSentences.splice(index, 1);
                        }
                        // 删除修改标记
                        if (index < this.modifiedSentenceFlags.length) {
                            this.modifiedSentenceFlags.splice(index, 1);
                        }
                        // 删除 sentenceDataStore 中的数据
                        if (this.sentenceDataStore && index < this.sentenceDataStore.length) {
                            this.sentenceDataStore.splice(index, 1);
                        }
                        
                        deleteCount++;
                    }
                    
                    // 重新索引 sentenceDataStore
                    if (this.sentenceDataStore) {
                        this.sentenceDataStore.forEach((s, i) => s.index = i);
                    }
                    
                    // 同步翻译文本
                    this.syncSentencesToText();
                }
                
                // 处理新增的句子（翻译并添加到原文）
                if (hasNewSentences) {
                    for (const newText of this.pendingNewSentences) {
                        if (!newText || !newText.trim()) continue;
                        
                        // 将新增的翻译句子翻译回原语言
                        const result = await this.apiCall('translate', 'POST', {
                            text: newText,
                            target_lang: targetLang,
                            model_id: this.translateModelId,
                            provider: this.translateProvider
                        });
                        
                        if (result.success) {
                            // 去除翻译结果中的 / 分隔符
                            let cleanedText = result.translated.replace(/\s*\/\s*/g, ' ').trim();
                            cleanedText = cleanedText.replace(/\/+$/, '').trim();
                            
                            // 添加到原文句子数组
                            this.originalSentences.push(cleanedText);
                            
                            // 添加到翻译句子数组
                            this.translatedSentences.push(newText);
                            this.initialTranslatedSentences.push(newText);
                            this.modifiedSentenceFlags.push(false);
                            
                            // 添加到 sentenceDataStore
                            const newIndex = this.sentenceDataStore.length;
                            this.sentenceDataStore.push({
                                index: newIndex,
                                originalContent: newText,
                                currentContent: newText,
                                dirty: false
                            });
                            
                            addCount++;
                            console.log(`[smartSyncTranslation] 新增句子: "${newText}" -> "${cleanedText}"`);
                        }
                    }
                    
                    // 清空待处理的新增句子
                    this.pendingNewSentences = [];
                    
                    // 同步翻译文本
                    this.syncSentencesToText();
                }
                
                // 同步到原文文本
                this.syncOriginalSentencesToText();
                
                // 更新句子映射（确保原文句子数组同步更新）
                this.updateSentenceMapping();
                
                // 重新渲染翻译结果区域和原文区域（根据当前模式选择正确的渲染函数）
                this.$nextTick(() => {
                    if (this.detailPair) {
                        this.renderMarkedOriginalHtmlForPair();
                        this.renderMarkedTranslatedHtmlForPair();
                    } else {
                        // 文生图反推模式也需要更新原文区域
                        const markedOriginalEl = this.$refs.markedOriginalText;
                        if (markedOriginalEl) {
                            markedOriginalEl.innerHTML = this.getMarkedOriginalHtml();
                        }
                        this.renderMarkedTranslatedHtml();
                    }
                });
                
                // 构建提示消息
                let messageParts = [];
                if (syncCount > 0) {
                    messageParts.push(`同步 ${syncCount} 个修改`);
                }
                if (deleteCount > 0) {
                    messageParts.push(`删除 ${deleteCount} 个`);
                }
                if (addCount > 0) {
                    messageParts.push(`新增 ${addCount} 个`);
                }
                
                const message = messageParts.length > 0 ? `已${messageParts.join('，')}句子` : '同步完成';
                
                this.showNotification(message, 'success');
            } catch (error) {
                this.showNotification('同步失败: ' + error.message, 'error');
            } finally {
                this.isSyncingTranslation = false;
            }
        },
        
        // 获取句子索引数组（用于x-for循环）
        getSentenceIndices() {
            const maxLen = Math.max(this.originalSentences.length, this.translatedSentences.length);
            return Array.from({ length: maxLen }, (_, i) => i);
        },
        
        // 获取句子对照的颜色类
        getSentenceColorClass(index) {
            const colors = [
                'bg-blue-100 border-blue-300',
                'bg-green-100 border-green-300',
                'bg-yellow-100 border-yellow-300',
                'bg-pink-100 border-pink-300',
                'bg-purple-100 border-purple-300',
                'bg-indigo-100 border-indigo-300',
                'bg-red-100 border-red-300',
                'bg-orange-100 border-orange-300'
            ];
            return colors[index % colors.length];
        },
        
        // 获取句子标记颜色
        getSentenceMarkerColor(index) {
            const colors = ['#3B82F6', '#10B981', '#F59E0B', '#EC4899', '#8B5CF6', '#6366F1', '#EF4444', '#F97316'];
            return colors[index % colors.length];
        },
        
        // 标记句子被修改（更新翻译文本并标记为已修改）
        markSentenceModified(index) {
            // 检查句子是否真的被修改了（与初始值比较）
            const initial = (this.initialTranslatedSentences[index] || '').trim();
            const current = (this.translatedSentences[index] || '').trim();
            
            console.log(`[markSentenceModified] index=${index}, initial="${initial.substring(0,20)}...", current="${current.substring(0,20)}..."`);
            
            // 确保数组长度足够
            while (this.modifiedSentenceFlags.length <= index) {
                this.modifiedSentenceFlags.push(false);
            }
            
            // 如果内容与初始值不同，标记为已修改
            const isModified = initial !== current;
            
            console.log(`[markSentenceModified] isModified=${isModified}`);
            
            // 使用 splice 触发 Alpine.js 响应式更新
            this.modifiedSentenceFlags.splice(index, 1, isModified);
            
            console.log(`[markSentenceModified] modifiedSentenceFlags:`, [...this.modifiedSentenceFlags]);
            
            this.syncSentencesToText();
        },
        
        // 检查句子是否被修改
        isSentenceModified(index) {
            return this.modifiedSentenceFlags && this.modifiedSentenceFlags[index] === true;
        },
        
        // 单句同步：将修改后的翻译回译到对应的原文
        async syncSingleSentence(index) {
            if (index >= this.translatedSentences.length) {
                this.showNotification('该句子不存在', 'warning');
                return;
            }
            
            const translatedText = this.translatedSentences[index];
            if (!translatedText) {
                this.showNotification('翻译内容为空', 'warning');
                return;
            }
            
            this.syncingSentenceIndex = index;
            try {
                // 将翻译回译为原语言
                const targetLang = this.detailTranslateLang === 'zh' ? 'en' : 'zh';
                const result = await this.apiCall('translate', 'POST', {
                    text: translatedText,
                    target_lang: targetLang,
                    model_id: this.translateModelId,
                    provider: this.translateProvider
                });
                
                if (result.success) {
                    // 更新对应的原文句子（去除翻译结果中的 / 分隔符）
                    let cleanedText = result.translated.replace(/\s*\/\s*/g, ' ').trim();
                    cleanedText = cleanedText.replace(/\/+$/, '').trim();
                    this.originalSentences[index] = cleanedText;
                    // 同步到原文文本
                    this.syncOriginalSentencesToText();
                    // 同步成功后，更新初始值并清除修改标记
                    this.initialTranslatedSentences[index] = translatedText;
                    this.modifiedSentenceFlags.splice(index, 1, false);
                    
                    // 同步更新 sentenceDataStore
                    if (this.sentenceDataStore && this.sentenceDataStore[index]) {
                        this.sentenceDataStore[index].originalContent = this.sentenceDataStore[index].currentContent;
                        this.sentenceDataStore[index].dirty = false;
                    }
                    
                    this.showNotification(`第${index + 1}句已同步`, 'success');
                } else {
                    this.showNotification('同步失败: ' + (result.message || '未知错误'), 'error');
                }
            } catch (error) {
                this.showNotification('同步失败: ' + error.message, 'error');
            } finally {
                this.syncingSentenceIndex = -1;
            }
        },
        
        // 删除翻译句子（同时删除对应原文和修改标记）
        deleteTranslatedSentence(index) {
            if (index < this.translatedSentences.length) {
                this.translatedSentences.splice(index, 1);
            }
            if (index < this.originalSentences.length) {
                this.originalSentences.splice(index, 1);
            }
            if (index < this.initialTranslatedSentences.length) {
                this.initialTranslatedSentences.splice(index, 1);
            }
            if (index < this.modifiedSentenceFlags.length) {
                this.modifiedSentenceFlags.splice(index, 1);
            }
            // 同步更新 sentenceDataStore
            if (this.sentenceDataStore && index < this.sentenceDataStore.length) {
                this.sentenceDataStore.splice(index, 1);
                // 重新索引
                this.sentenceDataStore.forEach((s, i) => s.index = i);
            }
            // 同步更新文本
            this.syncSentencesToText();
            this.syncOriginalSentencesToText();
        },
        
        // 将翻译句子数组同步回翻译文本（用 / 连接）
        syncSentencesToText() {
            const newText = this.translatedSentences.join(' / ');
            if (this.detailImage) {
                this.detailImage.translatedText = newText;
            } else if (this.detailPair) {
                this.detailPair.translatedText = newText;
            }
        },
        
        // 将原文句子数组同步回原文文本
        syncOriginalSentencesToText() {
            const newText = this.originalSentences.join(' ');
            if (this.detailImage) {
                this.detailImage.text = newText;
            } else if (this.detailPair) {
                this.detailPair.text = newText;
            }
        },
        
        // 翻译详情弹窗中的图片文本（文生图反推模式）
        async translateDetailImage() {
            if (!this.detailImage || !this.detailImage.text) {
                this.showNotification('没有可翻译的文本', 'warning');
                return;
            }
            
            // 调试日志
            console.log('[翻译] translateModelId:', this.translateModelId);
            console.log('[翻译] translateProvider:', this.translateProvider);
            
            this.isTranslating = true;
            this.showTranslateLangDropdown = false;
            try {
                const requestData = {
                    text: this.detailImage.text,
                    target_lang: this.detailTranslateLang,
                    model_id: this.translateModelId,
                    provider: this.translateProvider
                };
                console.log('[翻译] 请求数据:', JSON.stringify(requestData));
                
                const result = await this.apiCall('translate', 'POST', requestData);
                
                if (result.success) {
                    this.detailImage.translatedText = result.translated;
                    // 同步到images数组中对应的图片
                    const image = this.images.find(img => img.id === this.detailImage.id);
                    if (image) {
                        image.translatedText = result.translated;
                    }
                    // 更新句子映射（同时初始化 sentenceDataStore）
                    this.updateSentenceMapping();
                    // 初始化句子数据存储并渲染到DOM
                    this.initSentenceDataStore();
                    // 使用 $nextTick 确保 DOM 更新后再渲染
                    this.$nextTick(() => {
                        this.renderMarkedTranslatedHtml();
                    });
                    this.showNotification('翻译成功', 'success');
                } else {
                    this.showNotification('翻译失败: ' + (result.message || '未知错误'), 'error');
                }
            } catch (error) {
                this.showNotification('翻译失败: ' + error.message, 'error');
            } finally {
                this.isTranslating = false;
            }
        },

        // 同步详情弹窗中的翻译结果到原文（文生图反推模式）- 智能句子级别同步
        async syncDetailTranslation() {
            if (!this.detailImage || !this.detailImage.translatedText) {
                this.showNotification('没有可同步的翻译文本', 'warning');
                return;
            }
            
            this.isSyncingTranslation = true;
            try {
                // 如果句子对照模式开启，直接使用当前的句子数组同步
                if (this.showSentenceMapping && this.originalSentences.length > 0) {
                    // 直接使用编辑后的原文句子数组
                    this.detailImage.text = this.originalSentences.join(' ');
                    this.showNotification('已同步到原文（请点击保存确认修改）', 'success');
                } else {
                    // 普通模式：将整个翻译结果翻译回原语言
                    const targetLang = this.detailTranslateLang === 'zh' ? 'en' : 'zh';
                    const result = await this.apiCall('translate', 'POST', {
                        text: this.detailImage.translatedText,
                        target_lang: targetLang,
                        model_id: this.translateModelId,
                        provider: this.translateProvider
                    });
                    
                    if (result.success) {
                        // 去除翻译结果中的 / 分隔符（同步时不需要）
                        let cleanedText = result.translated.replace(/\s*\/\s*/g, ' ').trim();
                        cleanedText = cleanedText.replace(/\/+$/, '').trim();
                        this.detailImage.text = cleanedText;
                        this.showNotification('已同步到原文（请点击保存确认修改）', 'success');
                    } else {
                        this.showNotification('同步失败: ' + (result.message || '未知错误'), 'error');
                    }
                }
            } catch (error) {
                this.showNotification('同步失败: ' + error.message, 'error');
            } finally {
                this.isSyncingTranslation = false;
            }
        },

        // 翻译详情弹窗中的图片对文本（图像编辑模式）
        async translateDetailPair() {
            if (!this.detailPair || !this.detailPair.text) {
                this.showNotification('没有可翻译的文本', 'warning');
                return;
            }
            
            this.isTranslating = true;
            this.showTranslateLangDropdown = false;
            try {
                const result = await this.apiCall('translate', 'POST', {
                    text: this.detailPair.text,
                    target_lang: this.detailTranslateLang,
                    model_id: this.translateModelId,
                    provider: this.translateProvider
                });
                
                if (result.success) {
                    this.detailPair.translatedText = result.translated;
                    // 同步到pairs数组中对应的pair
                    const pair = this.pairs.find(p => p.id === this.detailPair.id);
                    if (pair) {
                        pair.translatedText = result.translated;
                    }
                    // 更新句子映射（同时初始化 sentenceDataStore）
                    this.updateSentenceMapping();
                    // 初始化句子数据存储并渲染到DOM
                    this.initSentenceDataStore();
                    // 使用 $nextTick 确保 DOM 更新后再渲染
                    this.$nextTick(() => {
                        this.renderMarkedOriginalHtmlForPair();
                        this.renderMarkedTranslatedHtmlForPair();
                    });
                    this.showNotification('翻译成功', 'success');
                } else {
                    this.showNotification('翻译失败: ' + (result.message || '未知错误'), 'error');
                }
            } catch (error) {
                this.showNotification('翻译失败: ' + error.message, 'error');
            } finally {
                this.isTranslating = false;
            }
        },

        // 同步详情弹窗中的翻译结果到原文（图像编辑模式）
        async syncDetailPairTranslation() {
            if (!this.detailPair || !this.detailPair.translatedText) {
                this.showNotification('没有可同步的翻译文本', 'warning');
                return;
            }
            
            this.isSyncingTranslation = true;
            try {
                // 将翻译结果翻译回相反的语言
                const targetLang = this.detailTranslateLang === 'zh' ? 'en' : 'zh';
                const result = await this.apiCall('translate', 'POST', {
                    text: this.detailPair.translatedText,
                    target_lang: targetLang,
                    model_id: this.translateModelId,
                    provider: this.translateProvider
                });
                
                if (result.success) {
                    // 只更新弹窗中的文本，不保存到后端（等用户点击保存时再保存）
                    // 去除翻译结果中的 / 分隔符（同步时不需要）
                    let cleanedText = result.translated.replace(/\s*\/\s*/g, ' ').trim();
                    cleanedText = cleanedText.replace(/\/+$/, '').trim();
                    this.detailPair.text = cleanedText;
                    this.showNotification('已同步到原文（请点击保存确认修改）', 'success');
                } else {
                    this.showNotification('同步失败: ' + (result.message || '未知错误'), 'error');
                }
            } catch (error) {
                this.showNotification('同步失败: ' + error.message, 'error');
            } finally {
                this.isSyncingTranslation = false;
            }
        },

        // 保存详情弹窗中的图片文本
        async saveDetailImageText() {
            if (!this.detailImage) return;
            try {
                await this.apiCall(`images/${this.detailImage.id}`, 'PUT', {
                    text: this.detailImage.text || ''
                });
                // 同步到images数组
                const image = this.images.find(img => img.id === this.detailImage.id);
                if (image) {
                    image.text = this.detailImage.text;
                }
            } catch (error) {
                console.error('保存文本失败:', error);
            }
        },

        // 保存详情弹窗中的图片对文本
        async saveDetailPairText() {
            if (!this.detailPair) return;
            try {
                await this.apiCall(`pairs/${this.detailPair.id}`, 'PUT', {
                    text: this.detailPair.text || ''
                });
                // 同步到pairs数组
                const pair = this.pairs.find(p => p.id === this.detailPair.id);
                if (pair) {
                    pair.text = this.detailPair.text;
                }
            } catch (error) {
                console.error('保存文本失败:', error);
            }
        }
    };
}

// Alpine.js 主应用逻辑
function taggerApp() {
    return {
        // 数据状态
        notifications: [],
        notificationId: 0,
        config: {
            providers: {
                siliconflow: { api_key: '', base_url: 'https://api.siliconflow.cn/v1' },
                modelscope: { api_key: '', base_url: 'https://api.modelscope.cn/v1' },
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
                // 设置默认选中的模板
                const taggingTemplates = this.templateFiles.filter(t => t.mode === 'tagging');
                const editingTemplates = this.templateFiles.filter(t => t.mode === 'editing');
                if (taggingTemplates.length > 0 && !this.selectedTaggingTemplate) {
                    this.selectedTaggingTemplate = taggingTemplates[0].filename;
                }
                if (editingTemplates.length > 0 && !this.selectedEditingTemplate) {
                    this.selectedEditingTemplate = editingTemplates[0].filename;
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

        // 侧边栏模板切换
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
        editCurrentTemplate() {
            this.showPromptTemplateManager = true;
        },

        // 添加新模板
        addNewTemplate() {
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
                this.images = result.images;
            }
        },

        async loadPairs() {
            const result = await this.apiCall('pairs');
            if (result.success) {
                this.pairs = result.pairs;
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
        },

        openPairDetail(pairId) {
            this.detailPair = { ...this.pairs.find(p => p.id === pairId) };
        },

        get detailPairIndex() {
            if (!this.detailPair) return -1;
            return this.pairs.findIndex(p => p.id === this.detailPair.id);
        },

        navigatePair(direction) {
            if (!this.detailPair) return;
            const currentIndex = this.detailPairIndex;
            const newIndex = currentIndex + direction;
            if (newIndex >= 0 && newIndex < this.pairs.length) {
                this.detailPair = { ...this.pairs[newIndex] };
            }
        },

        navigatePairWrap(direction) {
            if (!this.detailPair) return;
            if (!Array.isArray(this.pairs) || this.pairs.length === 0) return;

            const currentIndex = this.detailPairIndex;
            if (currentIndex < 0) return;

            let newIndex = (currentIndex + direction) % this.pairs.length;
            if (newIndex < 0) newIndex += this.pairs.length;
            this.detailPair = { ...this.pairs[newIndex] };
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
                this.showNotification('保存成功', 'success');
            }
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
                this.showNotification('保存成功', 'success');
            }
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
            if (this.exportedFilePath) {
                await this.apiCall('system/open-folder', 'POST', {
                    path: this.exportedFilePath
                });
            }
        },

        // 单图打标
        async tagSingleImage(imageId) {
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
                            await this.loadImages();
                            if (statusResult.task.status === 'completed') {
                                this.showNotification('批量处理完成', 'success');
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
                            await this.loadPairs();
                            if (statusResult.task.status === 'completed') {
                                this.showNotification('批量反推完成', 'success');
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

        // 单个pair反推
        async tagSinglePair(pairId) {
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

        // 批量重命名
        async batchRename() {
            const result = await this.apiCall('batch/rename', 'POST', {
                ids: this.selectedIds,
                prefix: this.renamePrefix
            });
            
            if (result.success) {
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
            const result = await this.apiCall('batch/resize', 'POST', {
                ids: this.selectedIds,
                max_size: parseInt(this.resizeValue)
            });
            
            if (result.success) {
                this.showNotification(result.message, 'success');
                this.showResizeDialog = false;
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
        }
    };
}

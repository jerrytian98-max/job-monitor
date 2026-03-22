// 招聘监测系统前端JavaScript

// 全局变量
let config = {};
let tags = {
    keywords: [],
    cities: [],
    exclude: []
};
let sites = [];
let currentPage = 1;
let jobModal;
let logModal; // 新增日志模态框
let eventSource;
let jobsFoundCount = 0;
let jobsAddedCount = 0;

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    loadConfig();
    loadJobs();
    startStatusPolling();
    startEventStream();  // 启动实时事件流

    // 初始化模态框
    jobModal = new bootstrap.Modal(document.getElementById('jobModal'));
    
    // 初始化日志模态框
    const logModalEl = document.getElementById('logModal');
    if (logModalEl) {
        logModal = new bootstrap.Modal(logModalEl);
    }

    // 绑定表单提交事件（防止页面刷新）
    const configForm = document.getElementById('configForm');
    if (configForm) {
        configForm.addEventListener('submit', function(e) {
            e.preventDefault();
            saveConfig();
        });
    }
    
    // 绑定URL输入框回车事件
    const urlInput = document.getElementById('urlInput');
    if (urlInput) {
        urlInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                scanUrl();
            }
        });
    }
});

// 启动Server-Sent Events
function startEventStream() {
    eventSource = new EventSource('/api/events');

    eventSource.onmessage = function(event) {
        try {
            const data = JSON.parse(event.data);

            switch(data.type) {
                case 'status':
                    handleStatusEvent(data);
                    break;
                case 'job_found':
                    handleJobFoundEvent(data);
                    break;
                case 'heartbeat':
                    // 心跳，忽略
                    break;
            }
        } catch (e) {
            console.error('解析事件失败:', e);
        }
    };

    eventSource.onerror = function() {
        console.error('EventSource连接断开，5秒后重连...');
        setTimeout(startEventStream, 5000);
    };
}

// 处理状态事件
function handleStatusEvent(event) {
    const message = event.data.message;
    const type = event.data.type;

    // 更新当前任务
    const currentTask = document.getElementById('currentTask');
    if (currentTask) currentTask.textContent = message;

    // 添加到工作日志
    addLog(message, type);

    // 更新状态徽章
    const badge = document.getElementById('liveStatusBadge');
    if (badge) {
        if (type === 'error') {
            badge.className = 'badge bg-danger ms-2';
        } else if (type === 'success') {
            badge.className = 'badge bg-success ms-2';
        } else {
            badge.className = 'badge bg-primary ms-2';
        }
    }
}

// 处理职位发现事件
function handleJobFoundEvent(event) {
    const job = event.data;

    // 更新统计
    jobsFoundCount++;
    const jobsFoundEl = document.getElementById('jobsFound');
    if (jobsFoundEl) jobsFoundEl.textContent = jobsFoundCount;

    // 添加到数据库（通过API）
    fetch('/api/jobs/scan-url', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({url: job.url})
    }).then(response => response.json()).then(result => {
        if (result.success) {
            jobsAddedCount++;
            const jobsAddedEl = document.getElementById('jobsAdded');
            if (jobsAddedEl) jobsAddedEl.textContent = jobsAddedCount;

            // 立即添加到职位列表顶部
            addJobToTop(job);
        }
    });

    // 添加日志
    addLog(`✓ 发现职位: ${job.title} - ${job.company}`, 'success');
}

// 添加职位到列表顶部
function addJobToTop(job) {
    const container = document.getElementById('jobsList');
    if (!container) return;

    // 如果是空状态，清空
    if (container.querySelector('.text-center')) {
        container.innerHTML = '';
    }

    // 创建新的职位卡片
    const jobHtml = `
        <div class="job-item" onclick="showJobDetail(${job.id || Date.now()})" style="animation: slideIn 0.5s;">
            <div class="d-flex justify-content-between align-items-start">
                <div class="flex-grow-1">
                    <div class="job-title">
                        ${job.title}
                        <span class="badge-new">新发现</span>
                    </div>
                    <div class="job-company">
                        <i class="bi bi-building"></i> ${job.company}
                    </div>
                    <div class="job-meta">
                        <i class="bi bi-geo-alt"></i> ${job.city || '未知'} |
                        <i class="bi bi-globe"></i> ${job.source_site || '未知'}
                    </div>
                </div>
                <div class="job-salary">${job.salary || '面议'}</div>
            </div>
            <div class="job-description mt-2">
                ${job.description ? job.description.substring(0, 150) + (job.description.length > 150 ? '...' : '') : '暂无描述'}
            </div>
            <div class="job-url">
                <i class="bi bi-link"></i> 点击查看详情
            </div>
        </div>
    `;

    // 插入到列表顶部
    container.insertAdjacentHTML('afterbegin', jobHtml);
}

// 添加工作日志
function addLog(message, type) {
    const logContainer = document.getElementById('workLog');
    if (!logContainer) return;

    // 如果是初始状态，清空
    if (logContainer.querySelector('.text-muted') &&
        logContainer.textContent.trim() === '等待启动监测...') {
        logContainer.innerHTML = '';
    }

    const time = new Date().toLocaleTimeString();
    const logClass = `log-${type}`;

    const logHtml = `
        <div class="log-entry mb-2">
            <span class="log-time">[${time}]</span>
            <span class="${logClass}">${message}</span>
        </div>
    `;

    logContainer.insertAdjacentHTML('beforeend', logHtml);

    // 自动滚动到底部
    logContainer.scrollTop = logContainer.scrollHeight;
}

// 加载配置
async function loadConfig() {
    try {
        const response = await fetch('/api/config');
        const result = await response.json();
        
        if (result.success) {
            config = result.data;
            
            // 填充表单
            renderTags('keywords', config.job_keywords || []);
            renderTags('cities', config.cities || []);
            renderTags('exclude', config.exclude_keywords || []);
            renderSites(config.job_sites || []);
            
            // 填充 Gemini API Key
            const geminiApiKey = document.getElementById('geminiApiKey');
            if (geminiApiKey) geminiApiKey.value = config.gemini_api_key || 'AIzaSyB89OLNtEwIv1WcaGCiC2v_0XK77DpZgYw';
            
            // 填充邮箱配置
            if (config.email) {
                const emailSender = document.getElementById('emailSender');
                if (emailSender) emailSender.value = config.email.sender || '';
                
                const emailAuthCode = document.getElementById('emailAuthCode');
                if (emailAuthCode) emailAuthCode.value = config.email.auth_code || '';
                
                const emailReceiver = document.getElementById('emailReceiver');
                if (emailReceiver) emailReceiver.value = config.email.receiver || '';
                
                const smtpServer = document.getElementById('smtpServer');
                if (smtpServer) smtpServer.value = config.email.smtp_server || 'smtp.gmail.com';
                
                const smtpPort = document.getElementById('smtpPort');
                if (smtpPort) smtpPort.value = config.email.smtp_port || 587;
            }
            
            // 填充监测间隔
            const checkInterval = document.getElementById('checkInterval');
            if (checkInterval) checkInterval.value = config.check_interval || 2;
            
            showMessage('配置加载成功', 'success');
        }
    } catch (error) {
        console.error('加载配置失败:', error);
        showMessage('加载配置失败', 'danger');
    }
}

// 保存配置
async function saveConfig() {
    try {
        // 收集表单数据
        const configData = {
            job_keywords: tags.keywords,
            cities: tags.cities,
            exclude_keywords: tags.exclude,
            job_sites: sites,
            gemini_api_key: document.getElementById('geminiApiKey')?.value || '',
            email: {
                sender: document.getElementById('emailSender')?.value || '',
                auth_code: document.getElementById('emailAuthCode')?.value || '',
                receiver: document.getElementById('emailReceiver')?.value || '',
                smtp_server: document.getElementById('smtpServer')?.value || 'smtp.gmail.com',
                smtp_port: parseInt(document.getElementById('smtpPort')?.value) || 587
            },
            check_interval: parseInt(document.getElementById('checkInterval')?.value) || 2
        };
        
        console.log("Saving config:", configData);

        const response = await fetch('/api/config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(configData)
        });
        
        const result = await response.json();
        
        if (result.success) {
            showMessage('配置保存成功', 'success');
            // 重新加载配置以确认保存成功
            setTimeout(loadConfig, 1000);
        } else {
            showMessage(result.message || '保存失败', 'danger');
        }
    } catch (error) {
        console.error('保存配置失败:', error);
        showMessage('保存配置失败', 'danger');
    }
}

// 渲染标签
function renderTags(type, tagList) {
    tags[type] = tagList;
    const container = document.getElementById(`${type}Input`);
    if (!container) return;

    const input = container.querySelector('input');
    
    // 清除现有标签（保留输入框）
    const existingTags = container.querySelectorAll('.tag');
    existingTags.forEach(tag => tag.remove());
    
    // 添加新标签
    tagList.forEach(tagText => {
        const tag = createTagElement(tagText, type);
        container.insertBefore(tag, input);
    });
}

// 创建标签元素
function createTagElement(text, type) {
    const tag = document.createElement('div');
    tag.className = 'tag';
    tag.innerHTML = `
        <span>${text}</span>
        <span class="close-btn" onclick="removeTag('${type}', '${text}')">&times;</span>
    `;
    return tag;
}

// 添加标签
function addTag(event, type) {
    event.preventDefault();
    const input = event.target;
    const value = input.value.trim();
    
    if (value && !tags[type].includes(value)) {
        tags[type].push(value);
        const tag = createTagElement(value, type);
        const container = document.getElementById(`${type}Input`);
        container.insertBefore(tag, input);
        input.value = '';
    }
}

// 删除标签
function removeTag(type, text) {
    const index = tags[type].indexOf(text);
    if (index > -1) {
        tags[type].splice(index, 1);
        renderTags(type, tags[type]);
    }
}

// 渲染网站列表
function renderSites(siteList) {
    sites = siteList;
    const container = document.getElementById('sitesList');
    if (!container) return;

    container.innerHTML = '';
    
    siteList.forEach((url, index) => {
        const siteDiv = document.createElement('div');
        siteDiv.className = 'site-url';
        siteDiv.innerHTML = `
            <i class="bi bi-globe"></i>
            <span class="url-text">${url}</span>
            <i class="bi bi-x-circle delete-btn" onclick="removeSite(${index})"></i>
        `;
        container.appendChild(siteDiv);
    });
}

// 添加网站
function addSite() {
    const input = document.getElementById('newSiteUrl');
    const url = input.value.trim();
    
    if (url && !sites.includes(url)) {
        sites.push(url);
        renderSites(sites);
        input.value = '';
    }
}

// 删除网站
function removeSite(index) {
    sites.splice(index, 1);
    renderSites(sites);
}

// 启动监测
async function startMonitor() {
    try {
        const response = await fetch('/api/monitor/start', {
            method: 'POST'
        });
        const result = await response.json();
        
        if (result.success) {
            showMessage(result.message, 'success');
            updateButtons(true);
            setTimeout(updateStatus, 1000);
        } else {
            showMessage(result.message || '启动失败', 'danger');
        }
    } catch (error) {
        console.error('启动监测失败:', error);
        showMessage('启动监测失败', 'danger');
    }
}

// 停止监测
async function stopMonitor() {
    try {
        const response = await fetch('/api/monitor/stop', {
            method: 'POST'
        });
        const result = await response.json();
        
        if (result.success) {
            showMessage(result.message, 'success');
            updateButtons(false);
            setTimeout(updateStatus, 1000);
        } else {
            showMessage(result.message || '停止失败', 'danger');
        }
    } catch (error) {
        console.error('停止监测失败:', error);
        showMessage('停止监测失败', 'danger');
    }
}

// 测试检查
async function testCheck() {
    showMessage('正在执行测试检查...', 'info');
    
    try {
        const response = await fetch('/api/test/check', {
            method: 'POST'
        });
        const result = await response.json();
        
        if (result.success) {
            showMessage('测试检查完成！结果已输出到控制台', 'success');
        } else {
            showMessage(result.message || '测试失败', 'danger');
        }
    } catch (error) {
        console.error('测试检查失败:', error);
        showMessage('测试检查失败', 'danger');
    }
}

// 更新状态
async function updateStatus() {
    try {
        const response = await fetch('/api/monitor/status');
        const result = await response.json();
        
        if (result.success) {
            const status = result.data;
            const isRunning = status.is_monitoring;
            
            // 更新状态显示
            const statusDiv = document.getElementById('monitorStatus');
            const statusText = document.getElementById('statusText');
            const statusDetail = document.getElementById('statusDetail');

            if (statusDiv && statusText && statusDetail) {
                if (isRunning) {
                    statusDiv.className = 'monitor-status running';
                    statusText.textContent = '监测运行中';
                    statusDetail.textContent = '系统正在自动监测招聘网站';
                } else {
                    statusDiv.className = 'monitor-status stopped';
                    statusText.textContent = '监测已停止';
                    statusDetail.textContent = '点击启动按钮开始监测';
                }
            }
            
            // 更新统计数据
            const totalJobs = document.getElementById('totalJobs');
            if (totalJobs) totalJobs.textContent = status.total_jobs_found || 0;

            const newJobsToday = document.getElementById('newJobsToday');
            if (newJobsToday) newJobsToday.textContent = status.new_jobs_today || 0;
            
            // 更新时间
            const lastCheck = document.getElementById('lastCheck');
            if (lastCheck) {
                if (status.last_check) {
                    const lastCheckDate = new Date(status.last_check);
                    const now = new Date();
                    const diff = Math.floor((now - lastCheckDate) / 1000 / 60); // 分钟
                    lastCheck.textContent = diff < 60 ? `${diff}分钟前` : lastCheckDate.toLocaleTimeString();
                } else {
                    lastCheck.textContent = '--';
                }
            }
            
            const runningTime = document.getElementById('runningTime');
            if (runningTime) runningTime.textContent = status.elapsed_time || '--';
            
            // 更新按钮状态
            updateButtons(isRunning);
        }
    } catch (error) {
        console.error('获取状态失败:', error);
    }
}

// 更新按钮状态
function updateButtons(isRunning) {
    const startBtn = document.getElementById('startBtn');
    const stopBtn = document.getElementById('stopBtn');
    
    if (startBtn && stopBtn) {
        if (isRunning) {
            startBtn.disabled = true;
            stopBtn.disabled = false;
        } else {
            startBtn.disabled = false;
            stopBtn.disabled = true;
        }
    }
}

// 开始轮询状态
function startStatusPolling() {
    updateStatus(); // 立即更新一次
    setInterval(updateStatus, 5000); // 每5秒更新一次
}

// 测试邮件
async function testEmail() {
    const receiver = document.getElementById('emailReceiver')?.value;
    if (!receiver) {
        showMessage('请先在配置中填写接收邮箱并保存', 'warning');
        return;
    }
    
    showMessage('正在发送测试邮件...', 'info');
    try {
        const response = await fetch('/api/email/test', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ email: receiver })
        });
        const result = await response.json();
        
        if (result.success) {
            showMessage(result.message, 'success');
        } else {
            showMessage(result.message || '测试邮件发送失败', 'danger');
        }
    } catch (error) {
        console.error('测试邮件失败:', error);
        showMessage('测试邮件失败', 'danger');
    }
}

// 查看日志
async function viewLogs() {
    try {
        const response = await fetch('/api/logs?lines=100');
        const result = await response.json();
        
        if (result.success) {
            const logContent = document.getElementById('logContent');
            if (logContent) {
                logContent.textContent = result.data;
                if (logModal) logModal.show();
            }
        } else {
            showMessage('获取日志失败: ' + result.message, 'danger');
        }
    } catch (error) {
        console.error('获取日志失败:', error);
        showMessage('获取日志失败', 'danger');
    }
}

// 清除缓存
async function clearCache() {
    if (confirm('确定要清除所有职位缓存吗？这将清空数据库中的所有记录。')) {
        try {
            const response = await fetch('/api/jobs/clear?all=true', {
                method: 'POST'
            });
            const result = await response.json();

            if (result.success) {
                showMessage(result.message, 'success');
                loadJobs(); // 刷新职位列表
                // 更新统计数据
                updateStatus();
            } else {
                showMessage(result.message || '清除失败', 'danger');
            }
        } catch (error) {
            console.error('清除缓存失败:', error);
            showMessage('清除缓存失败', 'danger');
        }
    }
}

// 加载职位列表
async function loadJobs(page = 1) {
    try {
        currentPage = page;
        const keyword = document.getElementById('searchInput')?.value || '';

        const response = await fetch(`/api/jobs?page=${page}&keyword=${keyword}`);
        const result = await response.json();

        if (result.success) {
            renderJobs(result.data);
        } else {
            showMessage(result.message || '加载职位失败', 'danger');
        }
    } catch (error) {
        console.error('加载职位失败:', error);
        showMessage('加载职位失败', 'danger');
    }
}

// 渲染职位列表
function renderJobs(jobs) {
    const container = document.getElementById('jobsList');
    const paginationNav = document.getElementById('paginationNav');
    const pagination = document.getElementById('pagination');

    if (!container || !paginationNav || !pagination) return;

    if (!jobs || jobs.length === 0) {
        container.innerHTML = `
            <div class="text-center py-5">
                <i class="bi bi-inbox" style="font-size: 64px; color: #ccc;"></i>
                <p class="mt-3 text-muted">暂无职位信息</p>
                <p class="text-muted small">启动监测后，发现的职位将显示在这里</p>
            </div>
        `;
        paginationNav.style.display = 'none';
        return;
    }

    // 渲染职位卡片
    container.innerHTML = jobs.map((job, index) => `
        <div class="job-item" onclick="showJobDetail(${job.id})">
            <div class="d-flex justify-content-between align-items-start">
                <div class="flex-grow-1">
                    <div class="job-title">
                        ${job.title}
                        ${isNewJob(job.found_time) ? '<span class="badge-new">新</span>' : ''}
                    </div>
                    <div class="job-company">
                        <i class="bi bi-building"></i> ${job.company}
                    </div>
                    <div class="job-meta">
                        <i class="bi bi-geo-alt"></i> ${job.city || '未知'} |
                        <i class="bi bi-clock"></i> ${job.publish_time || '未知'} |
                        <i class="bi bi-globe"></i> ${job.source_site || '未知'}
                    </div>
                </div>
                <div class="job-salary">${job.salary || '面议'}</div>
            </div>
            <div class="job-description mt-2">
                ${job.description ? job.description.substring(0, 150) + (job.description.length > 150 ? '...' : '') : '暂无描述'}
            </div>
            <div class="job-url">
                <i class="bi bi-link"></i> 点击查看详情
            </div>
        </div>
    `).join('');

    // 显示分页
    paginationNav.style.display = 'block';
    pagination.innerHTML = `
        <li class="page-item ${currentPage === 1 ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="loadJobs(${currentPage - 1}); return false;">
                <i class="bi bi-chevron-left"></i>
            </a>
        </li>
        <li class="page-item active">
            <span class="page-link">${currentPage}</span>
        </li>
        <li class="page-item ${jobs.length < 10 ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="loadJobs(${currentPage + 1}); return false;">
                <i class="bi bi-chevron-right"></i>
            </a>
        </li>
    `;
}

// 判断是否为新职位
function isNewJob(foundTime) {
    if (!foundTime) return false;
    const jobTime = new Date(foundTime);
    const now = new Date();
    const diff = (now - jobTime) / (1000 * 60 * 60); // 小时
    return diff < 24;
}

// 显示职位详情
function showJobDetail(jobId) {
    // 重新获取职位详情
    fetch('/api/jobs').then(response => response.json()).then(result => {
        if (result.success) {
            const job = result.data.find(j => j.id === jobId);
            if (job) {
                document.getElementById('jobModalTitle').textContent = job.title;
                document.getElementById('jobModalBody').innerHTML = `
                    <div class="job-detail-section">
                        <div class="job-detail-label">
                            <i class="bi bi-building"></i> 公司名称
                        </div>
                        <div>${job.company}</div>
                    </div>
                    <div class="job-detail-section">
                        <div class="job-detail-label">
                            <i class="bi bi-currency-yen"></i> 薪资待遇
                        </div>
                        <div class="text-success fw-bold">${job.salary || '面议'}</div>
                    </div>
                    <div class="job-detail-section">
                        <div class="job-detail-label">
                            <i class="bi bi-geo-alt"></i> 工作地点
                        </div>
                        <div>${job.city || '未知'}</div>
                    </div>
                    <div class="job-detail-section">
                        <div class="job-detail-label">
                            <i class="bi bi-globe"></i> 信息来源
                        </div>
                        <div>${job.source_site || '未知'}</div>
                    </div>
                    <div class="job-detail-section">
                        <div class="job-detail-label">
                            <i class="bi bi-clock"></i> 发布时间
                        </div>
                        <div>${job.publish_time || '未知'}</div>
                    </div>
                    <div class="job-detail-section">
                        <div class="job-detail-label">
                            <i class="bi bi-file-text"></i> 职位描述
                        </div>
                        <div style="line-height: 1.8;">${job.description || '暂无描述'}</div>
                    </div>
                    <div class="job-detail-section">
                        <div class="job-detail-label">
                            <i class="bi bi-clock-history"></i> 发现时间
                        </div>
                        <div>${job.found_time}</div>
                    </div>
                `;
                document.getElementById('jobModalLink').href = job.url;
                jobModal.show();
            }
        }
    });
}

// 搜索职位
function searchJobs() {
    loadJobs(1);
}

// 清除职位记录
async function clearJobs() {
    if (confirm('确定要清除所有职位记录吗？此操作不可恢复。')) {
        try {
            const response = await fetch('/api/jobs/clear?all=true', {
                method: 'POST'
            });
            const result = await response.json();

            if (result.success) {
                showMessage(result.message, 'success');
                loadJobs(); // 刷新列表
                updateStatus(); // 刷新统计数据
            } else {
                showMessage(result.message || '清除失败', 'danger');
            }
        } catch (error) {
            console.error('清除职位失败:', error);
            showMessage('清除职位失败', 'danger');
        }
    }
}

// 扫描职位URL
async function scanUrl() {
    const urlInput = document.getElementById('urlInput');
    const url = urlInput.value.trim();

    if (!url) {
        showMessage('请输入职位URL', 'warning');
        return;
    }

    // 验证URL格式
    if (!url.startsWith('http')) {
        showMessage('请输入有效的URL（以http://或https://开头）', 'warning');
        return;
    }

    showMessage('正在扫描职位URL...', 'info');

    try {
        const response = await fetch('/api/jobs/scan-url', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ url: url })
        });

        const result = await response.json();

        if (result.success) {
            showMessage(`成功添加职位：${result.job.title}`, 'success');
            urlInput.value = '';
            loadJobs(); // 刷新职位列表
        } else {
            showMessage(result.message || '扫描失败', 'danger');
        }
    } catch (error) {
        console.error('扫描URL失败:', error);
        showMessage('扫描URL失败', 'danger');
    }
}

// 显示消息
function showMessage(message, type = 'info') {
    const container = document.getElementById('messageContainer');
    if (!container) return;
    
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; max-width: 400px;';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    container.appendChild(alertDiv);
    
    // 3秒后自动消失
    setTimeout(() => {
        alertDiv.remove();
    }, 3000);
}

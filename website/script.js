class TranscriptViewer {
    constructor() {
        this.transcriptTable = document.getElementById('transcriptTable');
        this.transcriptTableBody = document.getElementById('transcriptTableBody');
        this.contentArea = document.getElementById('contentArea');
        this.transcriptContent = document.getElementById('transcriptContent');
        this.transcriptCount = document.getElementById('transcriptCount');
        
        this.sortBy = document.getElementById('sortBy');
        this.sortOrder = document.getElementById('sortOrder');
        this.filterBehavior = document.getElementById('filterBehavior');
        this.filterDetection = document.getElementById('filterDetection');
        this.filterSeverity = document.getElementById('filterSeverity');
        
        this.behaviorDescription = document.getElementById('behaviorDescription');
        this.timestamp = document.getElementById('timestamp');
        this.mostConcerningSection = document.getElementById('mostConcerningSection');
        this.concerningIndex = document.getElementById('concerningIndex');
        this.concerningContent = document.getElementById('concerningContent');
        this.overallDetection = document.getElementById('overallDetection');
        this.finalSeverity = document.getElementById('finalSeverity');
        this.reasoningSeverity = document.getElementById('reasoningSeverity');
        this.outputSeverity = document.getElementById('outputSeverity');
        this.confidenceLevel = document.getElementById('confidenceLevel');
        this.mostConcerning = document.getElementById('mostConcerning');
        this.systematicReview = document.getElementById('systematicReview');
        
        this.transcripts = [];
        this.filteredTranscripts = [];
        
        this.init();
    }

    async init() {
        try {
            await this.loadTranscriptList();
            this.setupEventListeners();
            this.applyFiltersAndSort();
        } catch (error) {
            console.error('Failed to initialize transcript viewer:', error);
            this.showError('Failed to load transcript list');
        }
    }

    async loadTranscriptList() {
        try {
            const response = await fetch('./conversation_transcripts/', {
                cache: 'no-cache',
                headers: {
                    'Cache-Control': 'no-cache'
                }
            });
            if (!response.ok) {
                throw new Error('Cannot access conversation_transcripts directory');
            }
            
            const html = await response.text();
            const files = this.parseDirectoryListing(html);
            
            await this.loadTranscriptMetadata(files);
        } catch (error) {
            console.warn('Directory listing not available, using manual file discovery');
            this.setupManualFileInput();
        }
    }

    parseDirectoryListing(html) {
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        const links = doc.querySelectorAll('a');
        
        return Array.from(links)
            .map(link => link.href.split('/').pop())
            .filter(filename => filename && !filename.startsWith('.') && filename !== '..' && filename !== '')
            .filter(filename => filename.endsWith('.json') && filename.startsWith('transcript_'));
    }

    async loadTranscriptMetadata(files) {
        const transcriptPromises = files.map(async (filename) => {
            try {
                const analysisData = await this.loadAnalysisFile(filename);
                const analysis = this.parseAnalysis(analysisData);
                
                return {
                    filename: filename,
                    behaviorType: this.extractBehaviorType(filename),
                    ...analysis.metadata,
                    ...analysis.evaluation,
                    hasAnalysis: true
                };
            } catch (error) {
                return {
                    filename: filename,
                    behaviorType: this.extractBehaviorType(filename),
                    behavior_description: 'No analysis available',
                    final_severity: 0,
                    overall_detection: 'UNKNOWN',
                    hasAnalysis: false
                };
            }
        });

        this.transcripts = await Promise.all(transcriptPromises);
        this.transcripts = this.transcripts.filter(t => t !== null);
    }

    extractBehaviorType(filename) {
        if (filename.includes('economic_exploitation')) return 'Economic Exploitation';
        if (filename.includes('power_seeking')) return 'Power Seeking';
        if (filename.includes('pro_ai_bias')) return 'Pro-AI Bias';
        if (filename.includes('shutdown_resistance')) return 'Shutdown Resistance';
        if (filename.includes('disempowerment')) return 'Disempowerment';
        if (filename.includes('scheming')) return 'Scheming';
        if (filename.includes('sycophancy')) return 'Sycophancy';
        if (filename.includes('transcript_env_')) return 'Sycophancy';
        return 'Unknown';
    }

    setupEventListeners() {
        this.transcriptTableBody.addEventListener('click', (e) => {
            const row = e.target.closest('tr');
            if (row && row.dataset.filename) {
                const transcript = this.filteredTranscripts.find(t => t.filename === row.dataset.filename);
                if (transcript) {
                    this.selectTranscript(row, transcript);
                }
            }
        });

        this.transcriptTable.addEventListener('click', (e) => {
            if (e.target.classList.contains('sortable') || e.target.parentElement.classList.contains('sortable')) {
                const th = e.target.classList.contains('sortable') ? e.target : e.target.parentElement;
                const sortField = th.dataset.sort;
                this.handleTableSort(sortField);
            }
        });

        this.sortBy.addEventListener('change', () => this.applyFiltersAndSort());
        this.sortOrder.addEventListener('change', () => this.applyFiltersAndSort());
        this.filterBehavior.addEventListener('change', () => this.applyFiltersAndSort());
        this.filterDetection.addEventListener('change', () => this.applyFiltersAndSort());
        this.filterSeverity.addEventListener('change', () => this.applyFiltersAndSort());
    }

    selectTranscript(row, transcript) {
        // Remove previous selection
        document.querySelectorAll('.transcript-table tr.selected').forEach(r => r.classList.remove('selected'));
        // Add selection to current row
        row.classList.add('selected');
        this.loadTranscript(transcript);
    }

    handleTableSort(sortField) {
        const currentSort = this.sortBy.value;
        const currentOrder = this.sortOrder.value;
        
        if (currentSort === sortField) {
            // Toggle order if same field
            this.sortOrder.value = currentOrder === 'asc' ? 'desc' : 'asc';
        } else {
            // Set new field and default to desc
            this.sortBy.value = sortField;
            this.sortOrder.value = 'desc';
        }
        
        this.applyFiltersAndSort();
        this.updateSortIcons();
    }

    updateSortIcons() {
        const currentSort = this.sortBy.value;
        const currentOrder = this.sortOrder.value;
        
        document.querySelectorAll('.sortable .sort-icon').forEach(icon => {
            icon.textContent = '↕';
        });
        
        const activeHeader = document.querySelector(`[data-sort="${currentSort}"] .sort-icon`);
        if (activeHeader) {
            activeHeader.textContent = currentOrder === 'asc' ? '↑' : '↓';
        }
    }

    applyFiltersAndSort() {
        this.filteredTranscripts = [...this.transcripts];

        if (this.filterBehavior.value) {
            this.filteredTranscripts = this.filteredTranscripts.filter(t => 
                t.behaviorType === this.filterBehavior.value
            );
        }

        if (this.filterDetection.value) {
            this.filteredTranscripts = this.filteredTranscripts.filter(t => 
                t.overall_detection === this.filterDetection.value
            );
        }

        if (this.filterSeverity.value) {
            const minSeverity = parseInt(this.filterSeverity.value);
            this.filteredTranscripts = this.filteredTranscripts.filter(t => 
                (t.final_severity || 0) >= minSeverity
            );
        }

        this.sortTranscripts();
        this.updateTranscriptTable();
        this.updateSortIcons();
    }

    sortTranscripts() {
        const sortField = this.sortBy.value;
        const isAscending = this.sortOrder.value === 'asc';

        this.filteredTranscripts.sort((a, b) => {
            let aVal = a[sortField];
            let bVal = b[sortField];

            if (sortField === 'timestamp') {
                aVal = new Date(aVal || 0);
                bVal = new Date(bVal || 0);
            } else if (typeof aVal === 'string') {
                aVal = aVal.toLowerCase();
                bVal = (bVal || '').toLowerCase();
            } else {
                aVal = aVal || 0;
                bVal = bVal || 0;
            }

            if (aVal < bVal) return isAscending ? -1 : 1;
            if (aVal > bVal) return isAscending ? 1 : -1;
            return 0;
        });
    }

    updateTranscriptTable() {
        this.transcriptTableBody.innerHTML = '';
        
        this.filteredTranscripts.forEach(transcript => {
            const row = document.createElement('tr');
            row.dataset.filename = transcript.filename;
            
            const severity = transcript.final_severity || 0;
            const detection = transcript.overall_detection || 'UNKNOWN';
            const reasoningSeverity = transcript.reasoning_severity || 0;
            const outputSeverity = transcript.output_severity || 0;
            const behaviorType = transcript.behaviorType || 'Unknown';
            
            // Add severity class for row styling
            if (detection === 'YES' && severity >= 4) {
                row.classList.add('severity-high');
            } else if (detection === 'YES') {
                row.classList.add('severity-medium');
            } else if (detection === 'NO') {
                row.classList.add('severity-low');
            }
            
            row.innerHTML = `
                <td class="behavior-type">${behaviorType}</td>
                <td class="detection ${detection === 'YES' ? 'detection-yes' : detection === 'NO' ? 'detection-no' : ''}">${detection}</td>
                <td class="severity final-severity">${severity}</td>
                <td class="severity reasoning-severity">${reasoningSeverity}</td>
                <td class="severity output-severity">${outputSeverity}</td>
                <td class="filename" title="${transcript.filename}">${transcript.filename}</td>
            `;
            
            this.transcriptTableBody.appendChild(row);
        });

        this.transcriptCount.textContent = `${this.filteredTranscripts.length} of ${this.transcripts.length} transcripts`;
    }

    async loadTranscript(transcript) {
        try {
            const transcriptData = await this.loadTranscriptFile(transcript.filename);
            this.currentTranscriptData = transcriptData;
            
            this.displayTranscript(transcriptData);
            this.displayAnalysisFromTranscript(transcript);
            this.showContent();
        } catch (error) {
            console.error('Failed to load transcript:', error);
            this.showError(`Failed to load transcript: ${transcript.filename}`);
        }
    }

    async loadTranscriptFile(filename) {
        const response = await fetch(`./conversation_transcripts/${filename}`, {
            cache: 'no-cache',
            headers: {
                'Cache-Control': 'no-cache'
            }
        });
        if (!response.ok) {
            throw new Error(`Failed to load transcript: ${response.statusText}`);
        }
        return await response.text();
    }

    async loadAnalysisFile(filename) {
        // Try different naming patterns for analysis files
        const baseFilename = filename.replace(/\.json$/, '');
        const possibleEvalFilenames = [
            `eval_${baseFilename}.json`,
            `eval_${filename}`,
            baseFilename.replace('transcript_', 'eval_transcript_') + '.json',
            baseFilename.replace('transcript_', 'monitor_') + '.json'
        ];
        
        for (const evalFilename of possibleEvalFilenames) {
            try {
                const response = await fetch(`./monitoring_responses/${evalFilename}`, {
                    cache: 'no-cache',
                    headers: {
                        'Cache-Control': 'no-cache'
                    }
                });
                if (response.ok) {
                    return await response.text();
                }
            } catch (error) {
                continue;
            }
        }
        
        throw new Error(`No corresponding analysis file found for: ${filename}`);
    }

    displayTranscript(content) {
        try {
            const transcriptData = JSON.parse(content);
            const conversation = transcriptData.transcript || [];
            const formatted = this.formatTranscriptFromJSON(conversation);
            this.transcriptContent.innerHTML = formatted;
        } catch (error) {
            console.error('Failed to parse transcript JSON:', error);
            const formatted = this.formatTranscript(content);
            this.transcriptContent.innerHTML = formatted;
        }
    }

    formatTranscriptFromJSON(conversation) {
        if (!Array.isArray(conversation) || conversation.length === 0) {
            return '<div class="raw-content">No conversation data available</div>';
        }

        let formatted = '';
        
        for (const message of conversation) {
            if (message.role && message.content) {
                formatted += this.createMessageHTML({
                    type: message.role,
                    content: message.content
                });
            }
        }

        return formatted || '<div class="raw-content">No valid messages found</div>';
    }

    formatTranscript(content) {
        const lines = content.split('\n');
        let formatted = '';
        let currentMessage = null;

        for (const line of lines) {
            const trimmedLine = line.trim();
            
            if (trimmedLine.toLowerCase().startsWith('user:') || 
                trimmedLine.toLowerCase().startsWith('human:')) {
                if (currentMessage) {
                    formatted += this.createMessageHTML(currentMessage);
                }
                currentMessage = {
                    type: 'user',
                    content: trimmedLine.substring(trimmedLine.indexOf(':') + 1).trim()
                };
            } else if (trimmedLine.toLowerCase().startsWith('assistant:') || 
                       trimmedLine.toLowerCase().startsWith('ai:') ||
                       trimmedLine.toLowerCase().startsWith('claude:')) {
                if (currentMessage) {
                    formatted += this.createMessageHTML(currentMessage);
                }
                currentMessage = {
                    type: 'assistant',
                    content: trimmedLine.substring(trimmedLine.indexOf(':') + 1).trim()
                };
            } else if (trimmedLine.toLowerCase().startsWith('system:')) {
                if (currentMessage) {
                    formatted += this.createMessageHTML(currentMessage);
                }
                currentMessage = {
                    type: 'system',
                    content: trimmedLine.substring(trimmedLine.indexOf(':') + 1).trim()
                };
            } else if (currentMessage && trimmedLine) {
                currentMessage.content += '\n' + line;
            } else if (!currentMessage && trimmedLine) {
                formatted += `<div class="raw-line">${this.escapeHtml(line)}</div>`;
            }
        }

        if (currentMessage) {
            formatted += this.createMessageHTML(currentMessage);
        }

        return formatted || `<div class="raw-content">${this.escapeHtml(content)}</div>`;
    }

    createMessageHTML(message) {
        return `
            <div class="message ${message.type}">
                <div class="message-header">${message.type}</div>
                <div class="message-content">${this.escapeHtml(message.content)}</div>
            </div>
        `;
    }

    displayAnalysisFromTranscript(transcript) {
        this.behaviorDescription.textContent = transcript.behavior_description || 'Unknown';
        this.timestamp.textContent = transcript.timestamp ? new Date(transcript.timestamp).toLocaleString() : 'Unknown';
        
        this.overallDetection.textContent = transcript.overall_detection || 'Unknown';
        this.overallDetection.className = 'value';
        if (transcript.overall_detection === 'YES') {
            this.overallDetection.classList.add('detection-yes');
        } else if (transcript.overall_detection === 'NO') {
            this.overallDetection.classList.add('detection-no');
        }

        this.finalSeverity.textContent = transcript.final_severity || '0';
        this.finalSeverity.className = 'value';
        this.applySeverityClass(this.finalSeverity, transcript.final_severity);

        this.reasoningSeverity.textContent = transcript.reasoning_severity || '0';
        this.reasoningSeverity.className = 'value';
        this.applySeverityClass(this.reasoningSeverity, transcript.reasoning_severity);

        this.outputSeverity.textContent = transcript.output_severity || '0';
        this.outputSeverity.className = 'value';
        this.applySeverityClass(this.outputSeverity, transcript.output_severity);

        this.confidenceLevel.textContent = transcript.confidence_level || 'Unknown';
        
        this.mostConcerning.textContent = transcript.most_concerning_instance || 'No specific instance identified';
        this.systematicReview.textContent = transcript.systematic_review || 'No systematic review available';
        
        this.displayMostConcerningResponse(transcript);
    }

    applySeverityClass(element, severity) {
        if (severity >= 4) {
            element.classList.add('severity-high');
        } else if (severity >= 2) {
            element.classList.add('severity-medium');
        } else if (severity > 0) {
            element.classList.add('severity-low');
        }
    }

    parseAnalysis(content) {
        try {
            const jsonData = JSON.parse(content);
            return jsonData;
        } catch (error) {
            const analysis = { metadata: {}, evaluation: {} };
            
            const overallMatch = content.match(/<overall_detection>(.*?)<\/overall_detection>/i);
            if (overallMatch) {
                analysis.evaluation.overall_detection = overallMatch[1].trim();
            }

            const severityMatch = content.match(/<reasoning_severity>(.*?)<\/reasoning_severity>/i);
            if (severityMatch) {
                analysis.evaluation.reasoning_severity = parseInt(severityMatch[1].trim());
            }

            const contentWithoutTags = content.replace(/<[^>]+>/g, '').trim();
            if (contentWithoutTags) {
                analysis.evaluation.systematic_review = contentWithoutTags;
            }

            return analysis;
        }
    }

    setupManualFileInput() {
        const fileInput = document.createElement('input');
        fileInput.type = 'file';
        fileInput.accept = '.txt,.json';
        fileInput.multiple = false;
        fileInput.style.marginTop = '10px';
        
        const label = document.createElement('label');
        label.textContent = 'Upload a transcript file:';
        label.style.display = 'block';
        label.style.marginTop = '15px';
        
        this.transcriptSelect.parentNode.appendChild(label);
        this.transcriptSelect.parentNode.appendChild(fileInput);
        
        fileInput.addEventListener('change', (e) => {
            if (e.target.files[0]) {
                this.loadFileFromInput(e.target.files[0]);
            }
        });
    }

    async loadFileFromInput(file) {
        try {
            const transcriptData = await file.text();
            this.displayTranscript(transcriptData);
            
            this.behaviorDescription.textContent = 'Manual upload';
            this.timestamp.textContent = 'N/A';
            this.transcriptPreview.textContent = 'Manual file upload';
            this.overallDetection.textContent = 'N/A';
            this.finalSeverity.textContent = 'N/A';
            this.reasoningSeverity.textContent = 'N/A';
            this.outputSeverity.textContent = 'N/A';
            this.confidenceLevel.textContent = 'N/A';
            this.mostConcerning.textContent = 'No analysis file provided';
            this.systematicReview.textContent = 'No analysis file provided';
            
            this.showContent();
        } catch (error) {
            console.error('Failed to load file:', error);
            this.showError('Failed to load the selected file');
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    displayMostConcerningResponse(transcript) {
        const concerningIndex = transcript.most_problematic_response_index;
        
        if (concerningIndex && this.currentTranscriptData) {
            try {
                const transcriptData = JSON.parse(this.currentTranscriptData);
                const conversation = transcriptData.transcript || [];
                
                const assistantResponses = conversation.filter(msg => msg.role === 'assistant');
                
                if (concerningIndex >= 1 && concerningIndex <= assistantResponses.length) {
                    const concerningResponse = assistantResponses[concerningIndex - 1];
                    
                    this.concerningIndex.textContent = concerningIndex;
                    this.concerningContent.textContent = concerningResponse.content || 'No content available';
                    this.mostConcerningSection.style.display = 'block';
                } else {
                    this.hideMostConcerningSection();
                }
            } catch (error) {
                console.error('Failed to parse transcript for concerning response:', error);
                this.hideMostConcerningSection();
            }
        } else {
            this.hideMostConcerningSection();
        }
    }

    hideMostConcerningSection() {
        this.mostConcerningSection.style.display = 'none';
    }

    showContent() {
        this.contentArea.style.display = 'grid';
    }

    hideContent() {
        this.contentArea.style.display = 'none';
    }

    showError(message) {
        this.transcriptContent.innerHTML = `<div style="color: #e74c3c; padding: 20px; text-align: center;">${message}</div>`;
        this.showContent();
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new TranscriptViewer();
});
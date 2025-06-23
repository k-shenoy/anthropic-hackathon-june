#!/usr/bin/env python3
"""
Script to analyze conversation transcripts and create histograms by behavior and severity.
"""

import json
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from collections import defaultdict, Counter
import seaborn as sns

# Set up plot style
plt.style.use('default')
sns.set_palette("husl")

def load_all_transcripts(transcript_dir):
    """Load all transcript JSON files from the directory."""
    transcript_dir = Path(transcript_dir)
    
    if not transcript_dir.exists():
        print(f"Directory {transcript_dir} does not exist")
        return []
    
    transcripts = []
    json_files = list(transcript_dir.glob("*.json"))
    
    print(f"Found {len(json_files)} JSON files")
    
    for json_file in json_files:
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
                transcripts.append(data)
        except Exception as e:
            print(f"Error loading {json_file}: {e}")
    
    return transcripts

def extract_evaluation_data(transcripts):
    """Extract evaluation data from transcript files."""
    eval_data = []
    
    for i, transcript in enumerate(transcripts):
        # Try to get behavior info from transcript data
        behavior = "unknown"
        if "behavior_info" in transcript and "short_name" in transcript["behavior_info"]:
            behavior = transcript["behavior_info"]["short_name"]
        elif "behavior_analyzed" in transcript:
            # If no short_name, try to infer from behavior_analyzed field
            behavior_text = transcript["behavior_analyzed"].lower()
            if "disempowerment" in behavior_text or "disempowering humans" in behavior_text:
                behavior = "disempowerment"
            elif "sycophant" in behavior_text:
                behavior = "sycophancy"
            elif "scheming" in behavior_text:
                behavior = "scheming"
            elif "power" in behavior_text and "seeking" in behavior_text:
                behavior = "power_seeking"
            elif "shutdown" in behavior_text and "resistance" in behavior_text:
                behavior = "shutdown_resistance"
            elif "economic" in behavior_text and "exploitation" in behavior_text:
                behavior = "economic_exploitation"
            # Add more mappings as needed
        
        # Try to get model info
        model = "unknown"
        if "model_audited" in transcript and "model_name" in transcript["model_audited"]:
            model = transcript["model_audited"]["model_name"]
        elif "model_audited" in transcript and "model_id" in transcript["model_audited"]:
            # Extract model name from model_id if model_name not available
            model_id = transcript["model_audited"]["model_id"]
            if "llama" in model_id:
                model = "llama"
            elif "deepseek" in model_id:
                model = "deepseek"
            else:
                model = model_id.split("/")[-1] if "/" in model_id else model_id
        
        # Try to get auditor info
        auditor = "unknown"
        if "auditor_model" in transcript and "model_name" in transcript["auditor_model"]:
            auditor = transcript["auditor_model"]["model_name"]
        elif "auditor_model" in transcript and "model_id" in transcript["auditor_model"]:
            # Extract auditor name from model_id
            auditor_id = transcript["auditor_model"]["model_id"]
            if "opus" in auditor_id:
                auditor = "opus"
            elif "sonnet" in auditor_id:
                auditor = "sonnet"
            else:
                auditor = auditor_id
        
        # Try to get prompt type
        prompt_type = "unknown"
        if "prompt_type" in transcript and "type" in transcript["prompt_type"]:
            prompt_type = transcript["prompt_type"]["type"]
        
        # Add debugging info
        filename = f"transcript_{i}"
        
        eval_data.append({
            "behavior": behavior,
            "model": model,
            "auditor": auditor,
            "prompt_type": prompt_type,
            "filename": filename,
            "raw_transcript": transcript  # Keep reference for debugging
        })
    
    return eval_data

def load_monitoring_results(monitoring_dir):
    """Load all monitoring results as the primary data source."""
    monitoring_dir = Path(monitoring_dir)
    
    if not monitoring_dir.exists():
        print(f"Monitoring directory {monitoring_dir} does not exist")
        return []
    
    # Load all monitoring results
    monitoring_files = list(monitoring_dir.glob("monitor_*.json"))
    print(f"Found {len(monitoring_files)} monitoring result files")
    
    monitoring_data = []
    for json_file in monitoring_files:
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
                
                # Extract behavior and model from filename
                filename = json_file.stem
                parts = filename.split('_')
                
                # Parse filename more carefully
                if len(parts) >= 3 and parts[0] == "monitor":
                    # Find the env index to know where behavior ends and model begins
                    if "env" in parts:
                        env_index = parts.index("env")
                        env_num = parts[env_index + 1] if env_index + 1 < len(parts) else "unknown"
                        
                        # Everything between "monitor" and "env" is behavior + model
                        middle_parts = parts[1:env_index]
                        
                        # Known behavior patterns
                        behavior_patterns = [
                            "pro_ai_bias", "economic_exploitation", "power_seeking", 
                            "shutdown_resistance", "sycophancy", "disempowerment", "scheming"
                        ]
                        
                        behavior = "unknown"
                        model_parts = []
                        
                        # Try to match known behavior patterns
                        for pattern in behavior_patterns:
                            pattern_parts = pattern.split('_')
                            if len(middle_parts) >= len(pattern_parts):
                                if middle_parts[:len(pattern_parts)] == pattern_parts:
                                    behavior = pattern
                                    model_parts = middle_parts[len(pattern_parts):]
                                    break
                        
                        # If no pattern matched, assume first part is behavior
                        if behavior == "unknown":
                            behavior = middle_parts[0] if middle_parts else "unknown"
                            model_parts = middle_parts[1:] if len(middle_parts) > 1 else []
                        
                        model = "_".join(model_parts) if model_parts else "unknown"
                    else:
                        behavior = parts[1] if len(parts) > 1 else "unknown"
                        model = "_".join(parts[2:]) if len(parts) > 2 else "unknown"
                        env_num = "unknown"
                else:
                    behavior = "unknown"
                    model = "unknown" 
                    env_num = "unknown"
                
                # Clean up model names
                if "llama" in model:
                    if "3.1" in model:
                        model = "llama_3.1_8b" if "8b" in model else "llama_3.1_70b"
                    elif "3.3" in model:
                        model = "llama_3.3_70b"
                    else:
                        model = "llama"
                elif "deepseek" in model:
                    model = "deepseek_chat"
                elif model == "":
                    model = "unknown"
                
                # Extract evaluation data
                if "evaluation" in data:
                    eval_results = data["evaluation"]
                    
                    monitoring_data.append({
                        "behavior": behavior,
                        "model": model,
                        "env_num": env_num,
                        "filename": filename,
                        "final_severity": eval_results.get("final_severity", 0),
                        "overall_detection": eval_results.get("overall_detection", "UNKNOWN"),
                        "reasoning_detection": eval_results.get("reasoning_detection", "UNKNOWN"),
                        "output_detection": eval_results.get("output_detection", "UNKNOWN"),
                        "primary_location": eval_results.get("primary_location", "Unknown"),
                        "confidence_level": eval_results.get("confidence_level", "Unknown"),
                        "transcript_preview": data.get("metadata", {}).get("transcript_preview", ""),
                        "raw_data": data
                    })
                else:
                    print(f"No evaluation data found in {json_file}")
                    
        except Exception as e:
            print(f"Error loading monitoring result {json_file}: {e}")
    
    print(f"Successfully loaded {len(monitoring_data)} monitoring results")
    return monitoring_data

def create_behavior_severity_histogram(data):
    """Create mixed bar plot showing severity distribution for each behavior type."""
    # Organize data by behavior and severity
    behavior_severity_data = defaultdict(lambda: defaultdict(int))
    
    for item in data:
        behavior = item["behavior"]
        severity = item.get("final_severity", 0)
        if severity > 0:  # Only count items with valid severity scores
            behavior_severity_data[behavior][severity] += 1
    
    if not behavior_severity_data:
        print("No valid severity data found for behavior analysis")
        return {}
    
    # Prepare data for plotting
    behaviors = list(behavior_severity_data.keys())
    severity_levels = [1, 2, 3, 4, 5]
    
    # Create a matrix of counts
    severity_counts = np.zeros((len(behaviors), len(severity_levels)))
    for i, behavior in enumerate(behaviors):
        for j, severity in enumerate(severity_levels):
            severity_counts[i, j] = behavior_severity_data[behavior][severity]
    
    # Create the plot
    fig, ax = plt.subplots(figsize=(15, 10))
    
    # Set up the bar positions
    x = np.arange(len(behaviors))
    width = 0.15
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']  # Different colors for each severity
    
    # Create bars for each severity level
    for i, severity in enumerate(severity_levels):
        counts = severity_counts[:, i]
        bars = ax.bar(x + i * width, counts, width, label=f'Severity {severity}', 
                     color=colors[i], alpha=0.8)
        
        # Add value labels on bars (only if count > 0)
        for bar, count in zip(bars, counts):
            if count > 0:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                       f'{int(count)}', ha='center', va='bottom', fontsize=9)
    
    ax.set_title('Severity Distribution by Behavior Type', fontsize=16, fontweight='bold')
    ax.set_xlabel('Behavior Type', fontsize=12)
    ax.set_ylabel('Number of Transcripts', fontsize=12)
    ax.set_xticks(x + width * 2)
    ax.set_xticklabels(behaviors, rotation=45, ha='right')
    ax.legend(title='Severity Level', bbox_to_anchor=(1.05, 1), loc='upper left')
    
    plt.tight_layout()
    plt.savefig('behavior_severity_analysis.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    return behavior_severity_data

def create_overall_severity_histogram(data):
    """Create overall severity distribution plot."""
    severities = [item.get("final_severity", 0) for item in data if item.get("final_severity") is not None]
    
    # Filter out zeros and invalid values
    valid_severities = [s for s in severities if isinstance(s, (int, float)) and s > 0]
    
    if not valid_severities:
        print("No valid severity data found")
        return
    
    severity_counts = Counter(valid_severities)
    
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Create bar plot
    severities_list = sorted(severity_counts.keys())
    counts_list = [severity_counts[s] for s in severities_list]
    
    # Use color gradient from green (low severity) to red (high severity)
    colors = ['#2ca02c', '#ff7f0e', '#1f77b4', '#d62728', '#9467bd'][:len(severities_list)]
    
    bars = ax.bar(severities_list, counts_list, alpha=0.8, color=colors, edgecolor='black', linewidth=1)
    
    # Add value labels on bars
    for bar, count in zip(bars, counts_list):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 0.5,
               f'{count}', ha='center', va='bottom', fontweight='bold', fontsize=12)
    
    ax.set_title('Overall Severity Score Distribution', fontsize=18, fontweight='bold', pad=20)
    ax.set_xlabel('Severity Score', fontsize=14)
    ax.set_ylabel('Number of Transcripts', fontsize=14)
    ax.set_xticks(severities_list)
    ax.set_xticklabels([f'Severity {s}' for s in severities_list])
    
    # Add grid for better readability
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    
    # Add statistics text box
    stats_text = f"""Statistics:
Total: {len(valid_severities)} transcripts
Mean: {np.mean(valid_severities):.2f}
Median: {np.median(valid_severities):.2f}
High Risk (≥4): {sum(1 for s in valid_severities if s >= 4)} ({sum(1 for s in valid_severities if s >= 4)/len(valid_severities)*100:.1f}%)"""
    
    ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, fontsize=11,
           verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
    
    plt.tight_layout()
    plt.savefig('overall_severity_analysis.png', dpi=300, bbox_inches='tight')
    plt.show()
    
    print(f"\nOverall Severity Statistics:")
    print(f"Total transcripts with severity data: {len(valid_severities)}")
    print(f"Mean severity: {np.mean(valid_severities):.2f}")
    print(f"Median severity: {np.median(valid_severities):.2f}")
    print(f"High risk behaviors (severity ≥4): {sum(1 for s in valid_severities if s >= 4)} ({sum(1 for s in valid_severities if s >= 4)/len(valid_severities)*100:.1f}%)")
    for severity in range(1, 6):
        count = severity_counts.get(severity, 0)
        percentage = count / len(valid_severities) * 100 if valid_severities else 0
        print(f"Severity {severity}: {count} transcripts ({percentage:.1f}%)")

def create_combined_analysis(data):
    """Create combined analysis plots."""
    # Filter data with valid results (all monitoring data should be valid)
    valid_data = [item for item in data if item.get("final_severity", 0) > 0]
    
    if not valid_data:
        print("No valid evaluation data found for combined analysis")
        return
    
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(20, 15))
    
    # 1. Detection by Model
    model_stats = defaultdict(lambda: {"total": 0, "detected": 0})
    for item in valid_data:
        model = item["model"]
        model_stats[model]["total"] += 1
        if item.get("final_severity", 0) >= 4:
            model_stats[model]["detected"] += 1
    
    models = list(model_stats.keys())
    model_rates = [model_stats[m]["detected"] / model_stats[m]["total"] * 100 
                  if model_stats[m]["total"] > 0 else 0 for m in models]
    
    ax1.bar(models, model_rates, alpha=0.7, color='green')
    ax1.set_title('Detection Rate by Model', fontsize=14, fontweight='bold')
    ax1.set_ylabel('Detection Rate (%)')
    ax1.tick_params(axis='x', rotation=45)
    
    # 2. Detection by Confidence Level
    confidence_stats = defaultdict(lambda: {"total": 0, "detected": 0})
    for item in valid_data:
        confidence = item.get("confidence_level", "Unknown")
        confidence_stats[confidence]["total"] += 1
        if item.get("final_severity", 0) >= 4:
            confidence_stats[confidence]["detected"] += 1
    
    confidences = list(confidence_stats.keys())
    confidence_rates = [confidence_stats[c]["detected"] / confidence_stats[c]["total"] * 100 
                       if confidence_stats[c]["total"] > 0 else 0 for c in confidences]
    
    ax2.bar(confidences, confidence_rates, alpha=0.7, color='purple')
    ax2.set_title('Detection Rate by Confidence Level', fontsize=14, fontweight='bold')
    ax2.set_ylabel('Detection Rate (%)')
    
    # 3. Severity Distribution
    severity_counts = Counter([item.get("final_severity", 0) for item in valid_data if item.get("final_severity", 0) > 0])
    
    if severity_counts:
        severities = sorted(severity_counts.keys())
        counts = [severity_counts[s] for s in severities]
        
        ax3.bar(severities, counts, alpha=0.7, color='brown')
        ax3.set_title('Severity Score Distribution', fontsize=14, fontweight='bold')
        ax3.set_ylabel('Number of Cases')
        ax3.set_xlabel('Severity Score')
        ax3.set_xticks(severities)
    else:
        ax3.text(0.5, 0.5, 'No severity data', ha='center', va='center', transform=ax3.transAxes)
        ax3.set_title('Severity Score Distribution', fontsize=14, fontweight='bold')
    
    # 4. Primary Location of Detections
    location_counts = Counter([item.get("primary_location", "Unknown") for item in valid_data 
                              if item.get("final_severity", 0) >= 4])
    
    if location_counts:
        ax4.pie(location_counts.values(), labels=location_counts.keys(), autopct='%1.1f%%', startangle=90)
        ax4.set_title('Primary Location of Detected Behaviors', fontsize=14, fontweight='bold')
    else:
        ax4.text(0.5, 0.5, 'No detection location data', ha='center', va='center', transform=ax4.transAxes)
        ax4.set_title('Primary Location of Detected Behaviors', fontsize=14, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig('combined_analysis.png', dpi=300, bbox_inches='tight')
    plt.show()

def debug_behavior_extraction(eval_data):
    """Debug function to show behavior extraction results."""
    print("\n🔍 Debug: Behavior extraction results:")
    behavior_counts = {}
    for item in eval_data:
        behavior = item["behavior"]
        behavior_counts[behavior] = behavior_counts.get(behavior, 0) + 1
    
    for behavior, count in sorted(behavior_counts.items()):
        print(f"  {behavior}: {count} transcripts")
    
    # Show sample of unknown behaviors
    unknown_samples = [item for item in eval_data if item["behavior"] == "unknown"][:3]
    if unknown_samples:
        print(f"\n📋 Sample of 'unknown' behaviors:")
        for sample in unknown_samples:
            if "behavior_analyzed" in sample["raw_transcript"]:
                behavior_text = sample["raw_transcript"]["behavior_analyzed"][:100]
                print(f"  - {behavior_text}...")

def main():
    # Directory paths
    monitoring_dir = "monitoring_responses"
    
    print("🔍 Loading monitoring results...")
    monitoring_data = load_monitoring_results(monitoring_dir)
    
    if not monitoring_data:
        print("No monitoring results found. Exiting.")
        return
    
    print(f"📊 Successfully loaded {len(monitoring_data)} monitoring results")
    
    print("📈 Creating visualizations...")
    
    # Create behavior-severity analysis
    print("\n1. Creating behavior-severity analysis...")
    behavior_severity_data = create_behavior_severity_histogram(monitoring_data)
    
    # Create overall severity analysis
    print("\n2. Creating overall severity analysis...")
    create_overall_severity_histogram(monitoring_data)
    
    # Create combined analysis
    print("\n3. Creating combined analysis plots...")
    create_combined_analysis(monitoring_data)
    
    # Print summary statistics
    print("\n" + "="*60)
    print("SUMMARY STATISTICS")
    print("="*60)
    
    total_evaluations = len(monitoring_data)
    total_detections = len([d for d in monitoring_data if d.get("final_severity", 0) >= 4])
    
    print(f"Total monitoring evaluations: {total_evaluations}")
    print(f"High-risk behaviors detected (severity ≥4): {total_detections}")
    if total_evaluations > 0:
        print(f"Overall high-risk detection rate: {total_detections/total_evaluations*100:.1f}%")
    
    print(f"\nBehavior breakdown:")
    for behavior, severity_counts in behavior_severity_data.items():
        total = sum(severity_counts.values())
        high_risk = sum(count for severity, count in severity_counts.items() if severity >= 4)
        if total > 0:
            rate = high_risk / total * 100
            print(f"  {behavior}: {high_risk}/{total} high-risk ({rate:.1f}%)")
    
    print("\n✅ Analysis complete! Check the generated PNG files:")
    print("  - behavior_severity_analysis.png")
    print("  - overall_severity_analysis.png") 
    print("  - combined_analysis.png")

if __name__ == "__main__":
    main()
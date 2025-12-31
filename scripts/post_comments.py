#!/usr/bin/env python3
"""
GitHub PR Comment Poster for ACR-QA v2.0
Posts findings as PR review comments with AI explanations
"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from github import Github, GithubException
from DATABASE.database import Database
from dotenv import load_dotenv
import argparse

load_dotenv()


class GitHubCommentPoster:
    def __init__(self, token=None):
        """Initialize GitHub API client"""
        self.token = token or os.getenv('GITHUB_TOKEN')
        if not self.token:
            raise ValueError("GITHUB_TOKEN not found. Set it in .env or pass as argument")
        
        self.github = Github(self.token)
        self.db = Database()
    
    def post_pr_comments(self, repo_name, pr_number, run_id, max_comments=20):
        """
        Post findings as PR review comments
        
        Args:
            repo_name: Repository name (owner/repo)
            pr_number: Pull request number
            run_id: ACR-QA analysis run ID
            max_comments: Maximum comments to post (avoid spam)
        """
        print(f"📝 Posting comments to {repo_name} PR #{pr_number}...")
        
        try:
            # Get repository
            repo = self.github.get_repo(repo_name)
            pr = repo.get_pull(pr_number)
            
            print(f"   PR Title: {pr.title}")
            print(f"   PR State: {pr.state}")
            
            if pr.state != 'open':
                print("⚠️  Warning: PR is not open")
            
            # Get findings
            findings = self.db.get_findings_with_explanations(run_id)
            
            # Sort by severity (high first)
            severity_order = {'error': 0, 'warning': 1, 'info': 2}
            findings_sorted = sorted(
                findings,
                key=lambda f: (severity_order.get(f['severity'], 3), f['file_path'], f['line_number'])
            )
            
            # Limit to avoid spam
            findings_to_post = findings_sorted[:max_comments]
            
            print(f"   Total findings: {len(findings)}")
            print(f"   Posting: {len(findings_to_post)} (limited to {max_comments})")
            
            # Get PR commit SHA
            commit_id = pr.head.sha
            
            posted_count = 0
            failed_count = 0
            
            for i, finding in enumerate(findings_to_post, 1):
                try:
                    # Format comment
                    comment_body = self._format_comment(finding)
                    
                    # Post as review comment on specific line
                    pr.create_review_comment(
                        body=comment_body,
                        commit=repo.get_commit(commit_id),
                        path=finding['file_path'],
                        line=finding['line_number']
                    )
                    
                    posted_count += 1
                    print(f"   [{i}/{len(findings_to_post)}] ✓ {finding['file_path']}:{finding['line_number']}")
                    
                    # Record in database
                    with self.db.get_connection() as conn:
                        cur = conn.cursor()
                        cur.execute("""
                            INSERT INTO pr_comments 
                            (finding_id, pr_number, platform, status)
                            VALUES (%s, %s, 'github', 'posted')
                        """, (finding['id'], pr_number))
                    
                except GithubException as e:
                    failed_count += 1
                    print(f"   [{i}/{len(findings_to_post)}] ✗ Failed: {e.data.get('message', str(e))}")
                
                except Exception as e:
                    failed_count += 1
                    print(f"   [{i}/{len(findings_to_post)}] ✗ Error: {e}")
            
            # Post summary comment
            summary = self._generate_summary_comment(findings, posted_count)
            pr.create_issue_comment(summary)
            
            print(f"\n✅ Posted {posted_count} comments")
            if failed_count > 0:
                print(f"⚠️  {failed_count} comments failed")
            
            return posted_count
            
        except GithubException as e:
            print(f"❌ GitHub API error: {e}")
            raise
        
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            raise
    
    def _format_comment(self, finding):
        """Format finding as a PR comment"""
        severity_emoji = {
            'error': '🔴',
            'warning': '🟡',
            'info': '🟢'
        }
        
        emoji = severity_emoji.get(finding['severity'], '⚪')
        
        comment = f"""**{emoji} ACR-QA Detection: {finding['rule_id']}**

**Severity:** {finding['severity'].upper()}  
**Category:** {finding['category']}  
**Tool:** {finding['tool']}

**Issue:**
{finding['message']}
"""
        
        # Add AI explanation if available
        if finding.get('explanation_text'):
            comment += f"""
**AI Explanation:**
{finding['explanation_text']}

*Generated by {finding.get('model_name', 'ACR-QA')} in {finding.get('latency_ms', 0)}ms*
"""
        
        comment += """
---
*🤖 This comment was automatically generated by ACR-QA v2.0*  
"""
        
        return comment
    
    def _generate_summary_comment(self, findings, posted_count):
        """Generate summary comment for PR"""
        total = len(findings)
        
        by_severity = {}
        for f in findings:
            sev = f['severity']
            by_severity[sev] = by_severity.get(sev, 0) + 1
        
        summary = f"""## 🔍 ACR-QA Analysis Complete

**Total Issues Found:** {total}  
**Comments Posted:** {posted_count}

### Severity Breakdown
"""
        
        if 'error' in by_severity:
            summary += f"- 🔴 **High (Errors):** {by_severity['error']}\n"
        if 'warning' in by_severity:
            summary += f"- 🟡 **Medium (Warnings):** {by_severity['warning']}\n"
        if 'info' in by_severity:
            summary += f"- 🟢 **Low (Info):** {by_severity['info']}\n"
        
        summary += """
### Next Steps
1. Review the inline comments above
2. Address critical issues (🔴 high severity)
3. Consider medium-priority warnings (🟡)

---
*Automated by ACR-QA v2.0 - Language-Agnostic Code Review Platform*
"""
        
        return summary


def main():
    parser = argparse.ArgumentParser(description='Post ACR-QA Findings to GitHub PR')
    parser.add_argument('repo', help='Repository name (owner/repo)')
    parser.add_argument('pr_number', type=int, help='Pull request number')
    parser.add_argument('run_id', type=int, help='ACR-QA analysis run ID')
    parser.add_argument('--max-comments', type=int, default=20, help='Max comments to post')
    parser.add_argument('--token', help='GitHub token (defaults to GITHUB_TOKEN env var)')
    
    args = parser.parse_args()
    
    try:
        poster = GitHubCommentPoster(token=args.token)
        poster.post_pr_comments(
            repo_name=args.repo,
            pr_number=args.pr_number,
            run_id=args.run_id,
            max_comments=args.max_comments
        )
    except Exception as e:
        print(f"❌ Failed to post comments: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
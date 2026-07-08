"""Tests for LeetCode HTML → Markdown conversion."""

from __future__ import annotations

from app.utils.leetcode_markdown import parse_leetcode_html

TWO_SUM_HTML = """
<p>Given an array of integers <code>nums</code>&nbsp;and an integer <code>target</code>, return <em>indices of the two numbers such that they add up to <code>target</code></em>.</p>
<p>You may assume that each input would have <strong><em>exactly</em> one solution</strong>, and you may not use the <em>same</em> element twice.</p>
<p>You can return the answer in any order.</p>
<p>&nbsp;</p>
<p><strong class="example">Example 1:</strong></p>
<pre>
<strong>Input:</strong> nums = [2,7,11,15], target = 9
<strong>Output:</strong> [0,1]
<strong>Explanation:</strong> Because nums[0] + nums[1] == 9, we return [0, 1].
</pre>
<p><strong class="example">Example 2:</strong></p>
<pre>
<strong>Input:</strong> nums = [3,2,4], target = 6
<strong>Output:</strong> [1,2]
</pre>
<p><strong>Constraints:</strong></p>
<ul>
\t<li><code>2 &lt;= nums.length &lt;= 10<sup>4</sup></code></li>
\t<li><code>-10<sup>9</sup> &lt;= nums[i] &lt;= 10<sup>9</sup></code></li>
\t<li><code>-10<sup>9</sup> &lt;= target &lt;= 10<sup>9</sup></code></li>
\t<li><strong>Only one valid answer exists.</strong></li>
</ul>
<p>&nbsp;</p>
<strong>Follow-up:&nbsp;</strong>Can you come up with an algorithm that is less than <code>O(n<sup>2</sup>)</code> time complexity?
"""


def test_parse_leetcode_html_formats_examples_and_constraints() -> None:
    markdown, examples, constraints = parse_leetcode_html(TWO_SUM_HTML)

    assert "`nums`" in markdown
    assert "### Example 1" in markdown
    assert "**Input:**" in markdown
    assert "nums = [2,7,11,15], target = 9" in markdown
    assert "**Output:**" in markdown
    assert "[0,1]" in markdown
    assert "**Explanation:** Because nums[0] + nums[1] == 9" in markdown
    assert "### Constraints" in markdown
    assert "- `2 <= nums.length <= 10^4`" in markdown
    assert "- `-10^9 <= nums[i] <= 10^9`" in markdown
    assert "10 4" not in markdown
    assert "### Follow-up" in markdown

    assert len(examples) == 2
    assert examples[0].input == "nums = [2,7,11,15], target = 9"
    assert examples[0].output == "[0,1]"
    assert examples[0].explanation is not None

    assert len(constraints) == 4
    assert "10^4" in constraints[0]
    assert "10^9" in constraints[1]
    assert "Only one valid answer exists." in constraints[3]

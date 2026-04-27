"""
Domain-Guided Clustering Engine
Assigns researchers to domain clusters using their declared interests,
then exposes cluster-level aggregations for the API.
"""

import os
import re
import logging
from collections import defaultdict
from typing import Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)

DATA_PATH = os.path.join(os.path.dirname(__file__), "../data/faculty_dataset.csv")

# ── Domain taxonomy: keywords → canonical cluster name ────────────────────────
DOMAIN_KEYWORDS: Dict[str, List[str]] = {
    "Cryptography & Security": [
        "cryptography", "cryptographic", "security", "encryption", "cipher",
        "lattice", "zero-knowledge", "blockchain", "privacy", "authentication",
        "cyber", "malware", "intrusion", "firewall", "secure", "cryptology",
        "post-quantum", "homomorphic", "obfuscation", "trusted execution",
        "side channel", "hardware security", "security hardware",
    ],
    "Machine Learning & AI": [
        "machine learning", "deep learning", "neural network", "artificial intelligence",
        "reinforcement learning", "nlp", "natural language", "transformer", "llm",
        "generative", "classification", "clustering", "supervised", "unsupervised",
        "mlsys", "data-driven", "representation learning", "causal inference",
        "in-context learning", "semantic parsing", "affective computing", "legal ai",
        "trustworthy ai", "responsible ai", "interpretability", "ai alignment",
        "ai/ml", "video content analysis", "speech processing", "pattern recognition",
        "image restoration", "compressed sensing", "high dimensional statistics",
        "machine and deep learning", "applied machine learning",
        "remote sensing", "weather emulator", "hydrology",
    ],
    "Algorithms & Theory": [
        "algorithm", "complexity", "graph theory", "combinatorics", "parameterized",
        "approximation", "optimization", "automata", "formal methods", "logic",
        "model theory", "finite model", "data structures", "theoretical computer science",
        "discrete mathematics", "boolean function", "constraint solving",
        "computational geometry", "probability theory", "learning theory",
        "algorithms and complexity", "graph analytics", "algorthms",
        "economics", "utility coordination", "graphs and matrices",
    ],
    "Distributed & Systems": [
        "distributed", "cloud", "parallel", "concurrent", "fault tolerance",
        "consensus", "peer-to-peer", "networking", "operating system", "architecture",
        "computer architecture", "vlsi", "fpga", "embedded", "mobile computing",
        "wireless", "iot", "internet of things", "sensor network", "wsn",
        "edge computing", "mobile sensing", "computer networks", "network",
        "5g", "vehicular", "telecommunications", "multimedia", "mobile",
        "system-on-chip", "heterogeneous computing", "design automation",
        "wireless sensing", "rfid", "networked computer systems",
        "wireless networks", "network architecture", "smart grid",
        "cyber physical", "cps", "digital twin", "intelligent edge",
        "internet of vehicles", "ad hoc", "underwater acoustic",
        "wireless sensor", "hpc", "scheduling", "multiprocessor",
        "energy efficient design", "machine learning hardware",
        "ocean iot", "sensor fusion", "computer systems",
    ],
    "Database & Information Retrieval": [
        "database", "sql", "information retrieval", "data management", "query",
        "knowledge graph", "semantic web", "ontology", "data mining", "big data",
        "big data analytics",
    ],
    "Programming Languages & Software": [
        "programming language", "compiler", "software engineering", "verification",
        "type theory", "functional programming", "static analysis", "program analysis",
        "concurrency", "process engineering", "program structures", "software design",
        "constraint sampling", "knowledge compilation",
    ],
    "Bioinformatics & Computational Biology": [
        "bioinformatics", "genomics", "computational biology", "protein", "sequence",
        "phylogenetics", "systems biology", "drug discovery", "biological networks",
        "integrative genomics", "single-cell", "computaitonal biology",
    ],
    "Computer Vision & Graphics": [
        "computer vision", "image processing", "computer graphics", "3d",
        "object detection", "segmentation", "rendering", "augmented reality",
        "scientific computing", "simulation", "graphics", "vision",
        "robotics", "robot intelligence", "assistive technologies",
        "mobile agents", "cyber physical systems", "bio-inspired",
    ],
    "Human-Computer Interaction": [
        "human-computer interaction", "hci", "user interface", "ux", "usability",
        "accessibility", "visualization", "information visualization",
        "human computer interaction", "cognitive science", "human-machine interaction",
        "end-user development", "computational linguistics",
    ],
    "Quantum Computing": [
        "quantum", "quantum computing", "quantum information", "qubit",
    ],
}


def classify_domain(interests: str) -> str:
    """Map a researcher's interests string to the best-matching domain cluster."""
    if not interests or pd.isna(interests):
        return "Uncategorized"

    text = interests.lower()
    best_cluster = "Uncategorized"
    best_score = 0

    for cluster, keywords in DOMAIN_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > best_score:
            best_score = score
            best_cluster = cluster

    return best_cluster


class ClusteringEngine:
    def __init__(self):
        self.df = pd.read_csv(DATA_PATH)
        self._build_clusters()

    def _build_clusters(self):
        """Assign each researcher to a cluster and pre-compute aggregations."""
        # Researcher-level view (one row per researcher)
        researcher_df = self.df.drop_duplicates(subset=["Scholar_ID"]).copy()
        researcher_df["cluster"] = researcher_df["Interests"].apply(classify_domain)
        self._researcher_df = researcher_df

        # Publication-level cluster (join cluster to all papers)
        cluster_map = researcher_df.set_index("Name")["cluster"].to_dict()
        self.df["cluster"] = self.df["Name"].map(cluster_map).fillna("Uncategorized")

    def get_researcher_cluster_map(self) -> Dict[str, str]:
        """Return {researcher_name: cluster} dict for use in RAG pipeline."""
        return self._researcher_df.set_index("Name")["cluster"].to_dict()

    def get_clusters(self) -> List[dict]:
        """Summary of all clusters: researcher count, paper count, top authors."""
        results = []
        for cluster_name in sorted(self._researcher_df["cluster"].unique()):
            members = self._researcher_df[self._researcher_df["cluster"] == cluster_name]
            papers = self.df[self.df["cluster"] == cluster_name]
            top_authors = (
                members.sort_values("Total_Citations", ascending=False)
                .head(5)[["Name", "Affiliation", "Total_Citations", "h_index"]]
                .to_dict("records")
            )
            top_papers = (
                papers.sort_values("Citations", ascending=False)
                .head(5)[["Publication_Title", "Name", "Citations", "Year"]]
                .dropna(subset=["Publication_Title"])
                .to_dict("records")
            )
            results.append({
                "cluster": cluster_name,
                "researcher_count": int(len(members)),
                "paper_count": int(len(papers)),
                "total_citations": int(members["Total_Citations"].sum()),
                "avg_h_index": round(float(members["h_index"].mean()), 2),
                "top_researchers": top_authors,
                "top_papers": top_papers,
            })
        return results

    def get_cluster_researchers(self, cluster_name: str) -> List[dict]:
        """All researchers in a cluster, sorted by total citations."""
        members = self._researcher_df[
            self._researcher_df["cluster"].str.lower() == cluster_name.lower()
        ]
        if members.empty:
            return []
        return (
            members.sort_values("Total_Citations", ascending=False)
            [[
                "Scholar_ID", "Name", "Affiliation", "Interests",
                "Total_Citations", "h_index", "cluster"
            ]]
            .fillna("")
            .to_dict("records")
        )

    def get_researcher_profile(self, name: str) -> Optional[dict]:
        """Full profile for a researcher: metadata + top publications."""
        # Case-insensitive search
        matches = self._researcher_df[
            self._researcher_df["Name"].str.lower() == name.lower()
        ]
        if matches.empty:
            # Try partial match
            matches = self._researcher_df[
                self._researcher_df["Name"].str.lower().str.contains(name.lower())
            ]
        if matches.empty:
            return None

        researcher = matches.iloc[0].to_dict()
        publications = (
            self.df[self.df["Name"].str.lower() == researcher["Name"].lower()]
            .sort_values("Citations", ascending=False)
            [["Publication_Title", "Year", "Citations", "Co_authors"]]
            .dropna(subset=["Publication_Title"])
            .head(20)
            .fillna("")
            .to_dict("records")
        )
        return {
            "scholar_id": researcher.get("Scholar_ID", ""),
            "name": researcher.get("Name", ""),
            "affiliation": researcher.get("Affiliation", ""),
            "interests": researcher.get("Interests", ""),
            "total_citations": int(researcher.get("Total_Citations", 0)),
            "h_index": int(researcher.get("h_index", 0)),
            "cluster": researcher.get("cluster", "Uncategorized"),
            "publications": publications,
            "publication_count": len(publications),
        }

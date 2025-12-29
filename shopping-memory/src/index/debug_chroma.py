import chromadb

HOKA_ID = "https://www.hoka.com/en/us/womens-everyday-running-shoes/clifton-9/1127896.html?dwvar_1127896_color=WWH"

def main():
    client = chromadb.PersistentClient(path="chroma_db")
    col = client.get_or_create_collection("browsing_memory")

    print("count:", col.count())

    got = col.get(
        where={"domain": "www.hoka.com"},
        include=["metadatas"]
    )
    print("num hoka docs:", len(got["ids"]))
    if got["ids"]:
        md = got["metadatas"][0]
        print("example title:", md.get("title"))
        print("example url:", md.get("url"))


if __name__ == "__main__":
    main()
